"""Deterministic stub writer — runs the loop with no model spend.

Not meant to be good copy; meant to prove the pipeline end to end. Swap for a
real model with WRITER_PROVIDER=openai_compat.
"""

from __future__ import annotations

from typing import ClassVar

from azul.enums import HookType
from azul.writing.base import Draft, DraftRequest, Writer


class StubWriter(Writer):
    name: ClassVar[str] = "stub"

    def write(self, request: DraftRequest) -> Draft:
        p = request.prospect
        greeting = f"Hi {p.first_name}," if p.first_name else "Hi,"
        ask = "Worth a quick 15 min next week?"
        if request.step > 1:
            line = "Circling back on my last note — still think it's worth a chat."
            return Draft(
                body=f"{greeting}\n\n{line} {ask}", subject=None, angle="follow-up",
                hook_type=HookType.AUTRE,
            )
        hook_line = request.hook or f"Been following {p.company or 'your work'}."
        body = f"{greeting}\n\n{hook_line}\n\n{ask}"
        subject = f"quick thought on {p.company}" if p.company else "quick thought"
        return Draft(body=body, subject=subject, angle="hook-led", hook_type=HookType.AUTRE)
