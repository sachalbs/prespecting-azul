"""Holo3 computer-use research: drive a headless browser to find real hooks.

Loop: screenshot -> Holo3 returns an action (click/type/scroll/navigate) or a
final answer -> execute in Playwright -> re-screenshot -> ... until done.
LinkedIn is browsed via a logged-in session (LINKEDIN_STORAGE_STATE).

⚠️ TODO(holo-guide): the action JSON schema, coordinate convention and final-answer
shape below are a best-effort reconstruction of the Holo3 "agent loop guide" (which
is bot-walled here). Reconcile `_HOLO_SYSTEM`, `_parse_action` and `_execute_action`
with the official guide, then verify locally. Until confirmed, parsing failures
raise loudly rather than fabricate hooks. Coordinates assumed ABSOLUTE PIXELS,
origin top-left, on a 1280x800 viewport.
"""

from __future__ import annotations

import base64
import json
import time
from typing import TYPE_CHECKING, Any, ClassVar

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from azul.config import get_settings
from azul.domain import ProspectBrief
from azul.errors import ConfigError, ResearchError
from azul.logging import get_logger
from azul.research.base import Hook, ResearchEngine, ResearchResult

if TYPE_CHECKING:
    from playwright.sync_api import Page

log = get_logger(__name__)

_MAX_IMAGES = 3  # image budget: keep only the most recent screenshots in context

# Principle #0: the objective is the specific, non-obvious hook — not the generic
# funding announcement. Keep this in sync with the playbook.
_HOLO_SYSTEM = """\
You are a research agent controlling a web browser to find ONE specific,
non-obvious hook about a person for cold outreach: a recent post, an opinion they
defend, a detail of their path — NOT a generic "congrats on the funding".

Each turn you receive a screenshot. Respond with a SINGLE JSON object:
  {"action":"navigate","url":"..."}        go to a URL
  {"action":"click","point":[x,y]}          click at absolute pixel coords
  {"action":"type","text":"..."}            type into the focused field
  {"action":"scroll","direction":"down"}    scroll (up|down)
  {"action":"wait"}                          wait for load
  {"action":"finish","hooks":[{"text":"...","rationale":"...","source_url":"..."}]}
Emit "finish" with 1-3 hooks as soon as you have enough. JSON only.
"""


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

    # ── Holo API ────────────────────────────────────────────────────────────
    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        reraise=True,
    )
    def _next_action(self, messages: list[dict[str, Any]]) -> str:
        resp = self._client.post(
            "/chat/completions",
            json={"model": self._model, "messages": messages, "temperature": 0},
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    @staticmethod
    def _parse_action(content: str) -> dict[str, Any]:
        # TODO(holo-guide): confirm exact shape. Tolerate JSON wrapped in prose.
        start, end = content.find("{"), content.rfind("}")
        if start == -1 or end == -1:
            raise ResearchError(f"Holo returned no JSON action: {content[:200]}")
        try:
            action = json.loads(content[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ResearchError(f"Holo action not valid JSON: {exc}") from exc
        if "action" not in action and "hooks" not in action:
            raise ResearchError(f"Holo action missing 'action'/'hooks': {action}")
        return action

    # ── browser execution ─────────────────────────────────────────────────────
    @staticmethod
    def _execute_action(page: Page, action: dict[str, Any]) -> None:
        kind = action.get("action")
        if kind == "navigate":
            page.goto(action["url"], wait_until="domcontentloaded")
        elif kind == "click":
            x, y = action["point"]
            page.mouse.click(float(x), float(y))
        elif kind == "type":
            page.keyboard.type(action.get("text", ""))
        elif kind == "scroll":
            dy = -600 if action.get("direction") == "up" else 600
            page.mouse.wheel(0, dy)
        elif kind == "wait":
            page.wait_for_timeout(1500)
        else:  # pragma: no cover - defensive
            raise ResearchError(f"Unknown Holo action: {kind}")

    @staticmethod
    def _screenshot_message(page: Page, note: str) -> dict[str, Any]:
        png = page.screenshot()
        b64 = base64.b64encode(png).decode()
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
                browser = pw.chromium.launch(headless=self._headless)
                ctx = browser.new_context(
                    storage_state=self._storage_state if self._storage_state else None,
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

                for _ in range(self._max_steps):
                    if time.monotonic() > deadline:
                        log.warning("holo_timeout", email=prospect.email)
                        break
                    content = self._next_action(messages)
                    transcript.append({"assistant": content})
                    action = self._parse_action(content)
                    if action.get("action") == "finish" or "hooks" in action:
                        hooks = [
                            Hook(
                                text=h.get("text", ""),
                                rationale=h.get("rationale"),
                                source_url=h.get("source_url"),
                                confidence=0.7,
                            )
                            for h in action.get("hooks", [])
                            if h.get("text")
                        ]
                        sources.append({"url": page.url})
                        browser.close()
                        return ResearchResult(
                            engine=self.name,
                            hooks=hooks,
                            sources=sources,
                            raw={"transcript": transcript},
                        )
                    self._execute_action(page, action)
                    sources.append({"url": page.url})
                    messages.append({"role": "assistant", "content": content})
                    messages.append(self._screenshot_message(page, "Result. Next action?"))
                    # Enforce the image budget: drop older screenshots.
                    _trim_images(messages, _MAX_IMAGES)
                browser.close()
        except ResearchError:
            raise
        except Exception as exc:  # pragma: no cover - browser/runtime failures
            log.error("holo_research_failed", email=prospect.email, error=str(exc))
            raise ResearchError(f"Holo research failed: {exc}") from exc

        # Clean fallback: nothing conclusive found.
        log.info("holo_no_hook", email=prospect.email)
        return ResearchResult(
            engine=self.name, hooks=[], sources=sources, raw={"transcript": transcript}
        )


def _trim_images(messages: list[dict[str, Any]], keep: int) -> None:
    """Strip image parts from all but the last `keep` image-bearing messages."""
    image_idxs = [
        i
        for i, m in enumerate(messages)
        if isinstance(m.get("content"), list)
        and any(part.get("type") == "image_url" for part in m["content"])
    ]
    for i in image_idxs[:-keep]:
        m = messages[i]
        m["content"] = [p for p in m["content"] if p.get("type") != "image_url"] or "[screenshot]"
