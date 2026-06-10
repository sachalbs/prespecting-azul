"""Writer backed by any OpenAI-compatible chat API (GLM-5.1, DeepSeek V4, …).

Provider is chosen purely via env (WRITER_BASE_URL / WRITER_MODEL / WRITER_API_KEY),
so swapping GLM <-> DeepSeek is a config change, never a code change.
"""

from __future__ import annotations

import json
from typing import Any, ClassVar

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from azul.config import get_settings
from azul.enums import HookType
from azul.errors import ConfigError, WritingError
from azul.logging import get_logger
from azul.writing.base import Draft, DraftRequest, Writer
from azul.writing.prompts import build_messages

log = get_logger(__name__)


class OpenAICompatWriter(Writer):
    name: ClassVar[str] = "openai_compat"

    def __init__(self, timeout: float = 60.0) -> None:
        s = get_settings()
        missing = [
            k
            for k, v in {
                "WRITER_API_KEY": s.writer_api_key,
                "WRITER_BASE_URL": s.writer_base_url,
                "WRITER_MODEL": s.writer_model,
            }.items()
            if not v
        ]
        if missing:
            raise ConfigError(f"WRITER_PROVIDER=openai_compat requires: {', '.join(missing)}")
        self._model = s.writer_model
        self._temperature = s.writer_temperature
        # Some OpenAI-compatible providers reject response_format with a 400;
        # remembered per instance so we only pay the failed round-trip once.
        self._json_mode = True
        self._client = httpx.Client(
            base_url=str(s.writer_base_url).rstrip("/"),
            headers={"Authorization": f"Bearer {s.writer_api_key}"},
            timeout=timeout,
        )

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=16),
        reraise=True,
    )
    def _complete(self, messages: list[dict[str, str]], json_mode: bool) -> str:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": self._temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        resp = self._client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data["choices"][0]["message"]["content"]

    def _complete_with_fallback(self, messages: list[dict[str, str]]) -> str:
        try:
            return self._complete(messages, self._json_mode)
        except httpx.HTTPStatusError as exc:
            if self._json_mode and exc.response.status_code == 400:
                log.warning("writer_json_mode_unsupported", model=self._model)
                self._json_mode = False
                return self._complete(messages, json_mode=False)
            raise

    @staticmethod
    def _parse(content: str) -> Draft:
        parsed = json.loads(content)
        body = (parsed.get("body") or "").strip()
        if not body:
            raise WritingError("Writer returned an empty body")
        subject = (parsed.get("subject") or "").strip() or None
        try:
            hook_type = HookType(str(parsed.get("hook_type") or ""))
        except ValueError:
            hook_type = HookType.AUTRE  # taxonomy is closed; junk lands in "autre"
        return Draft(
            body=body, subject=subject, angle=parsed.get("angle"), hook_type=hook_type
        )

    def write(self, request: DraftRequest) -> Draft:
        messages = build_messages(request)
        try:
            content = self._complete_with_fallback(messages)
        except httpx.HTTPError as exc:
            log.error("writer_failed", email=request.prospect.email, error=str(exc))
            raise WritingError(f"Writer call failed: {exc}") from exc

        try:
            return self._parse(content)
        except json.JSONDecodeError:
            # One retry: model JSON hiccups are common enough to not lose the prospect.
            log.warning("writer_bad_json_retry", email=request.prospect.email)
            try:
                return self._parse(self._complete_with_fallback(messages))
            except json.JSONDecodeError as exc:
                raise WritingError(f"Writer did not return valid JSON: {exc}") from exc
            except httpx.HTTPError as exc:
                raise WritingError(f"Writer call failed: {exc}") from exc
