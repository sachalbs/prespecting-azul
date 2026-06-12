"""Holo3 computer-use research: drive a headless browser to find real hooks.

Loop: screenshot -> Holo3 returns an action -> execute in Playwright -> re-screenshot
-> ... until task_complete. LinkedIn is browsed via a logged-in session
(LINKEDIN_STORAGE_STATE).

Agent-loop contract (per the Holo3 spec): each turn Holo returns either native
`tool_calls` or a JSON envelope {"note","thought","tool_call":{"name","arguments"}}.
Actions: click, type, scroll, drag_and_drop, key, task_complete, screenshot_request.
Coordinates are NORMALISED [0,1000] and remapped to the live viewport here. The
system prompt below *defines* the schema this parser expects, so prompt and parser
stay consistent; on any mismatch the raw message is logged for correction.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from azul.config import get_settings
from azul.costs import record_llm_usage
from azul.domain import ProspectBrief
from azul.errors import ConfigError, ResearchError
from azul.logging import get_logger
from azul.research.base import Hook, ResearchEngine, ResearchResult

if TYPE_CHECKING:
    from playwright.sync_api import Page

log = get_logger(__name__)

_MAX_IMAGES = 3  # image budget: keep only the most recent screenshots in context
_COORD_SCALE = 1000.0  # Holo coordinates are normalised to [0, 1000]
_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_HOLO_SYSTEM = """\
You are a research agent controlling a web browser to find ONE specific,
non-obvious hook about a person for cold outreach: a recent post, an opinion they
defend, a detail of their path — NOT a generic "congrats on the funding".

Each turn you receive a screenshot. Reply with a SINGLE JSON object:
  {"note":"...", "thought":"...", "tool_call":{"name":<action>, "arguments":{...}}}

Actions and arguments (coordinates are NORMALISED integers in [0,1000], origin
top-left):
  click            {"x":int,"y":int}
  type             {"text":str}                 (optionally {"x","y"} to click first)
  scroll           {"direction":"up"|"down"}
  key              {"key":"Enter"}
  drag_and_drop    {"start":[x,y],"end":[x,y]}
  goto             {"url":str}                  (navigate directly to a URL)
  screenshot_request {}                          (ask for a fresh screenshot)
  task_complete    {"hooks":[{"text":str,"rationale":str,"source_url":str}]}

Call task_complete with 1-3 hooks as soon as you have enough. JSON only.
"""


_MAX_CORRECTIONS = 2  # invalid replies tolerated before falling back to hooks=[]

# A fine-tuned computer-use model often speaks its own action dialect; map the
# probable aliases onto our canonical schema instead of failing the prospect.
_ACTION_ALIASES = {
    "left_click": "click",
    "double_click": "click",
    "mouse_click": "click",
    "tap": "click",
    "type_text": "type",
    "input_text": "type",
    "write": "type",
    "press_key": "key",
    "keypress": "key",
    "press": "key",
    "hotkey": "key",
    "wheel": "scroll",
    "scroll_up": "scroll",
    "scroll_down": "scroll",
    "drag": "drag_and_drop",
    "navigate": "goto",
    "open_url": "goto",
    "open": "goto",
    "finish": "task_complete",
    "done": "task_complete",
    "stop": "task_complete",
    "screenshot": "screenshot_request",
    "take_screenshot": "screenshot_request",
}

_KNOWN_ACTIONS = (
    "click",
    "type",
    "scroll",
    "key",
    "drag_and_drop",
    "goto",
    "screenshot_request",
    "task_complete",
)


def normalize_action(name: str, args: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Canonical action name + args (scroll_up/down carry their direction)."""
    raw = name.strip().lower()
    canonical = _ACTION_ALIASES.get(raw, raw)
    if raw == "scroll_up":
        args = {**args, "direction": "up"}
    elif raw == "scroll_down":
        args = {**args, "direction": "down"}
    return canonical, args


def _correction(error: Exception) -> dict[str, Any]:
    return {
        "role": "user",
        "content": (
            f"Your last reply was invalid: {error}. Reply with ONE JSON object exactly "
            f"per the schema. Valid actions: {', '.join(_KNOWN_ACTIONS)}."
        ),
    }


@dataclass
class HoloAction:
    name: str
    args: dict[str, Any] = field(default_factory=dict)
    note: str | None = None
    thought: str | None = None


def _extract_json(text: str) -> dict[str, Any]:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ResearchError(f"Holo returned no JSON: {text[:300]}")
    return json.loads(text[start : end + 1])


def parse_holo_message(message: dict[str, Any]) -> HoloAction:
    """Normalise a Holo chat message into an HoloAction (native tool_calls or JSON)."""
    tool_calls = message.get("tool_calls")
    if tool_calls:
        fn = tool_calls[0]["function"]
        raw_args = fn.get("arguments") or {}
        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        name, args = normalize_action(fn["name"], args or {})
        return HoloAction(name=name, args=args)

    content = message.get("content") or ""
    try:
        obj = _extract_json(content if isinstance(content, str) else json.dumps(content))
    except json.JSONDecodeError as exc:
        raise ResearchError(f"Holo content not valid JSON: {exc}") from exc

    call = obj.get("tool_call") or obj
    name = call.get("name") or call.get("action")
    if not name:
        raise ResearchError(f"Holo message missing tool_call name: {obj}")
    args = call.get("arguments")
    if args is None:
        args = {k: v for k, v in call.items() if k not in ("name", "action")}
    name, args = normalize_action(str(name), args)
    return HoloAction(name=name, args=args, note=obj.get("note"), thought=obj.get("thought"))


def remap_point(args: dict[str, Any], width: int, height: int) -> tuple[float, float]:
    """Normalised [0,1000] -> viewport pixels. Accepts x/y or coordinate/point lists."""
    if "x" in args and "y" in args:
        nx, ny = float(args["x"]), float(args["y"])
    else:
        for key in ("coordinate", "point", "position", "coord"):
            seq = args.get(key)
            if isinstance(seq, (list, tuple)) and len(seq) >= 2:
                nx, ny = float(seq[0]), float(seq[1])
                break
        else:
            raise ResearchError(f"Holo action has no coordinates: {args}")
    return nx / _COORD_SCALE * width, ny / _COORD_SCALE * height


def _pair(value: Any) -> tuple[float, float]:
    if isinstance(value, dict):
        return float(value["x"]), float(value["y"])
    return float(value[0]), float(value[1])


class Holo3ResearchEngine(ResearchEngine):
    name: ClassVar[str] = "holo3"

    def __init__(self, timeout: float = 60.0) -> None:
        s = get_settings()
        if not s.hai_api_key:
            raise ConfigError("HAI_API_KEY is required for RESEARCH_ENGINE=holo3")
        self._model = s.holo_model
        self._max_steps = s.holo_max_steps
        self._deadline_s = s.holo_timeout_s
        self._headless = s.holo_headless
        self._storage_state = s.linkedin_storage_state
        self._client = httpx.Client(
            base_url=s.holo_base_url.rstrip("/"),
            headers={"Authorization": f"Bearer {s.hai_api_key}"},
            timeout=timeout,
        )

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        reraise=True,
    )
    def _next_message(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        resp = self._client.post(
            "/chat/completions",
            json={"model": self._model, "messages": messages, "temperature": 0},
        )
        resp.raise_for_status()
        data = resp.json()
        record_llm_usage("holo", "research_step", data.get("usage"))
        return data["choices"][0]["message"]

    @staticmethod
    def _viewport(page: Page) -> tuple[int, int]:
        vp = page.viewport_size or {"width": 1280, "height": 720}
        return vp["width"], vp["height"]

    def _execute(self, page: Page, action: HoloAction) -> None:
        w, h = self._viewport(page)
        name, args = action.name, action.args
        if name in ("task_complete", "screenshot_request"):
            return
        if name == "click":
            page.mouse.click(*remap_point(args, w, h))
        elif name == "type":
            if "x" in args and "y" in args:
                page.mouse.click(*remap_point(args, w, h))
            page.keyboard.type(args.get("text", ""))
        elif name == "scroll":
            page.mouse.wheel(0, -600 if args.get("direction") == "up" else 600)
        elif name == "key":
            page.keyboard.press(args.get("key") or args.get("text") or "Enter")
        elif name == "drag_and_drop":
            x1, y1 = _pair(args["start"])
            x2, y2 = _pair(args["end"])
            page.mouse.move(x1 / _COORD_SCALE * w, y1 / _COORD_SCALE * h)
            page.mouse.down()
            page.mouse.move(x2 / _COORD_SCALE * w, y2 / _COORD_SCALE * h)
            page.mouse.up()
        elif name == "goto":
            url = args.get("url") or args.get("href") or args.get("text")
            if not url:
                raise ResearchError(f"goto needs a url, got: {args}")
            page.goto(str(url), wait_until="domcontentloaded")
        else:
            raise ResearchError(f"Unknown Holo action: {name}")

    @staticmethod
    def hooks_from_complete(action: HoloAction) -> list[Hook]:
        raw = action.args.get("hooks")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                raw = None
        if not isinstance(raw, list):
            # Fallback: salvage a single hook from the note/thought.
            text = action.note or action.thought
            return [Hook(text=text, confidence=0.5)] if text else []
        return [
            Hook(
                text=h.get("text", ""),
                rationale=h.get("rationale"),
                source_url=h.get("source_url"),
                confidence=0.7,
            )
            for h in raw
            if isinstance(h, dict) and h.get("text")
        ]

    @staticmethod
    def _screenshot_message(page: Page, note: str) -> dict[str, Any]:
        b64 = base64.b64encode(page.screenshot()).decode()
        return {
            "role": "user",
            "content": [
                {"type": "text", "text": note},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        }

    def _start_url(self, prospect: ProspectBrief) -> str:
        q = " ".join(filter(None, [prospect.full_name, prospect.company, "linkedin"]))
        return str(httpx.URL("https://www.google.com/search", params={"q": q}))

    def research(self, prospect: ProspectBrief) -> ResearchResult:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover
            raise ConfigError(
                "playwright not installed; run `playwright install chromium`"
            ) from exc

        transcript: list[dict[str, Any]] = []
        sources: list[dict[str, Any]] = []
        deadline = time.monotonic() + self._deadline_s

        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch(
                    headless=self._headless,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                ctx = browser.new_context(
                    storage_state=self._storage_state if self._storage_state else None,
                    user_agent=_USER_AGENT,
                    locale="en-US",
                )
                # Reduce trivial bot detection so Azul can browse real sites (incl. LinkedIn).
                ctx.add_init_script(
                    "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                )
                page = ctx.new_page()
                page.goto(self._start_url(prospect), wait_until="domcontentloaded")

                task = (
                    f"Find a specific, non-obvious hook about {prospect.full_name} "
                    f"({prospect.title or '?'} at {prospect.company or '?'}). "
                    f"Known dossier: {json.dumps(dict(prospect.signals), default=str)[:1500]}"
                )
                messages: list[dict[str, Any]] = [
                    {"role": "system", "content": _HOLO_SYSTEM},
                    {"role": "user", "content": task},
                    self._screenshot_message(page, "Current screen. Next action?"),
                ]

                corrections = 0
                for _ in range(self._max_steps):
                    if time.monotonic() > deadline:
                        log.warning("holo_timeout", email=prospect.email)
                        break
                    message = self._next_message(messages)
                    try:
                        action = parse_holo_message(message)
                    except ResearchError as exc:
                        # Invalid reply: tell the model what was wrong (max 2 times),
                        # then give up on THIS prospect with hooks=[] — never raise.
                        corrections += 1
                        if corrections > _MAX_CORRECTIONS:
                            log.error(
                                "holo_parse_failed", email=prospect.email, raw=str(message)[:800]
                            )
                            break
                        log.warning(
                            "holo_correction", email=prospect.email, attempt=corrections,
                            error=str(exc),
                        )
                        messages.append(_correction(exc))
                        continue
                    transcript.append({"action": action.name, "args": action.args})

                    if action.name == "task_complete":
                        sources.append({"url": page.url})
                        browser.close()
                        return ResearchResult(
                            engine=self.name,
                            hooks=self.hooks_from_complete(action),
                            sources=sources,
                            raw={"transcript": transcript},
                        )

                    if action.name != "screenshot_request":
                        try:
                            self._execute(page, action)
                        except ResearchError as exc:
                            corrections += 1
                            if corrections > _MAX_CORRECTIONS:
                                log.error(
                                    "holo_action_failed", email=prospect.email, error=str(exc)
                                )
                                break
                            log.warning(
                                "holo_correction", email=prospect.email, attempt=corrections,
                                error=str(exc),
                            )
                            messages.append(_correction(exc))
                            continue
                        sources.append({"url": page.url})
                    messages.append({"role": "assistant", "content": json.dumps(action.args)})
                    messages.append(self._screenshot_message(page, "Result. Next action?"))
                    _trim_images(messages, _MAX_IMAGES)
                browser.close()
        except ResearchError:
            raise
        except Exception as exc:  # pragma: no cover - browser/runtime failures
            log.error("holo_research_failed", email=prospect.email, error=str(exc))
            raise ResearchError(f"Holo research failed: {exc}") from exc

        log.info("holo_no_hook", email=prospect.email)
        return ResearchResult(
            engine=self.name, hooks=[], sources=sources, raw={"transcript": transcript}
        )


def _trim_images(messages: list[dict[str, Any]], keep: int) -> None:
    """Strip image parts from all but the last `keep` image-bearing messages."""
    idxs = [
        i
        for i, m in enumerate(messages)
        if isinstance(m.get("content"), list)
        and any(p.get("type") == "image_url" for p in m["content"])
    ]
    for i in idxs[:-keep]:
        m = messages[i]
        m["content"] = [p for p in m["content"] if p.get("type") != "image_url"] or "[screenshot]"
