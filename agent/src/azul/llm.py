"""Thin OpenAI-compatible chat helper on the writer credentials (DeepSeek default).

One JSON-returning call, shared by everything that needs the LLM outside the
Writer itself (brief conversation, discovery query generation, ICP scoring).
Mirrors the writer's hardening: transport retries, response_format fallback on
400, brace-extraction before json.loads.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from azul.config import get_settings
from azul.errors import ConfigError, LLMError
from azul.logging import get_logger

log = get_logger(__name__)


def _extract_json(text: str) -> dict[str, Any]:
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise LLMError(f"LLM returned no JSON: {text[:300]}")
    try:
        data: dict[str, Any] = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMError(f"LLM returned invalid JSON: {exc}") from exc
    return data


@retry(
    retry=retry_if_exception_type(httpx.TransportError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=16),
    reraise=True,
)
def _post(payload: dict[str, Any], base_url: str, api_key: str, timeout: float) -> httpx.Response:
    return httpx.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json=payload,
        timeout=timeout,
    )


def chat_json(
    messages: list[dict[str, str]], *, temperature: float = 0.3, timeout: float = 60.0
) -> dict[str, Any]:
    """One chat completion that must come back as a JSON object."""
    s = get_settings()
    if not (s.writer_base_url and s.writer_api_key and s.writer_model):
        raise ConfigError(
            "LLM calls need WRITER_BASE_URL / WRITER_MODEL / WRITER_API_KEY (DeepSeek default)"
        )
    payload: dict[str, Any] = {
        "model": s.writer_model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    try:
        resp = _post(payload, str(s.writer_base_url), str(s.writer_api_key), timeout)
        if resp.status_code == 400:  # provider rejects response_format -> plain retry
            payload.pop("response_format")
            resp = _post(payload, str(s.writer_base_url), str(s.writer_api_key), timeout)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    except httpx.HTTPError as exc:
        raise LLMError(f"LLM call failed: {exc}") from exc
    return _extract_json(str(content))
