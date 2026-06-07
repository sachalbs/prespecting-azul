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
    def _complete(self, messages: list[dict[str, str]]) -> str:
        resp = self._client.post(
            "/chat/completions",
            json={
                "model": self._model,
                "messages": messages,
                "temperature": self._temperature,
                "response_format": {"type": "json_object"},
            },
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
        return data["choices"][0]["message"]["content"]

    def write(self, request: DraftRequest) -> Draft:
        try:
            content = self._complete(build_messages(request))
        except httpx.HTTPError as exc:
            log.error("writer_failed", email=request.prospect.email, error=str(exc))
            raise WritingError(f"Writer call failed: {exc}") from exc

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise WritingError(f"Writer did not return valid JSON: {exc}") from exc

        body = (parsed.get("body") or "").strip()
        if not body:
            raise WritingError("Writer returned an empty body")
        subject = (parsed.get("subject") or "").strip() or None
        return Draft(body=body, subject=subject, angle=parsed.get("angle"))
