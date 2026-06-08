"""`azul chat` — the product surface: manage Azul like an employee, from chat.

A local conversational console that drives the same campaign engine. The
WhatsApp/Slack hook (via the Channel) plugs into this exact surface later; the
intent parser can graduate to the Writer/LLM. Kept deterministic for now so it
runs and is testable without any keys.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from azul.db.session import session_scope
from azul.orchestrator import campaign as camp

HELP = """\
I'm Azul. Manage me like an SDR. Commands:
  campaign <name> from <file.csv>   start a campaign (source -> research -> draft)
  show                              show the drafts waiting for your approval
  approve all | approve 1 3         approve drafts (numbers from `show`)
  edit <n> <new body>               replace a draft's body (your edit is logged)
  send [dry]                        send approved mail (paced, from your mailbox)
  sync                              pull replies/bounces into outcomes
  report                            the number that matters: reply rate
  help · quit
"""


@dataclass
class ChatSession:
    tenant: str = "me"
    sender: str | None = None
    campaign_id: uuid.UUID | None = None
    listing: list[uuid.UUID] = field(default_factory=list)

    def handle(self, line: str) -> str:
        line = line.strip()
        if not line:
            return ""
        cmd, _, rest = line.partition(" ")
        cmd = cmd.lower()
        rest = rest.strip()

        if cmd in ("help", "?"):
            return HELP
        if cmd in ("campaign", "new"):
            return self._campaign(rest)
        if cmd in ("show", "drafts", "review"):
            return self._show()
        if cmd == "approve":
            return self._approve(rest)
        if cmd == "edit":
            return self._edit(rest)
        if cmd == "send":
            return self._send(dry="dry" in rest.lower())
        if cmd in ("sync", "replies"):
            return self._sync()
        if cmd == "report":
            return self._report()
        return "Didn't catch that. Type `help`."

    # ── commands ──────────────────────────────────────────────────────────────
    def _campaign(self, rest: str) -> str:
        name, _, path = rest.partition(" from ")
        name, path = name.strip(), path.strip()
        if not name or not path:
            return "Usage: campaign <name> from <file.csv>"
        try:
            rows = camp.load_prospects_csv(path)
        except OSError as exc:
            return f"Can't read {path}: {exc}"
        with session_scope() as s:
            c = camp.run_campaign(
                s, tenant_slug=self.tenant, name=name, rows=rows, sender_name=self.sender
            )
            self.campaign_id = c.id
            drafts = len(camp.list_drafts(s, c.id))
        return f"Ran '{name}' on {len(rows)} prospects → {drafts} drafts ready. Type `show`."

    def _show(self) -> str:
        if self.campaign_id is None:
            return "No campaign yet. Start one: campaign <name> from <file.csv>"
        with session_scope() as s:
            drafts = camp.list_drafts(s, self.campaign_id)
            self.listing = [m.id for m in drafts]
            if not drafts:
                return "No drafts waiting."
            blocks = [
                f"[{i}] {m.prospect.email} ({m.prospect.company or '-'})\n"
                f"    subj: {m.subject or '-'}\n    {m.final_body.replace(chr(10), ' ')[:160]}"
                for i, m in enumerate(drafts, 1)
            ]
        return "\n".join(blocks) + "\n\napprove all · approve 1 3 · edit <n> <text>"

    def _resolve(self, rest: str) -> list[uuid.UUID]:
        ids: list[uuid.UUID] = []
        for tok in rest.split():
            if tok.isdigit() and 1 <= int(tok) <= len(self.listing):
                ids.append(self.listing[int(tok) - 1])
        return ids

    def _approve(self, rest: str) -> str:
        if self.campaign_id is None:
            return "Start a campaign first."
        with session_scope() as s:
            if rest.lower().strip() == "all":
                n = camp.approve(
                    s, campaign_id=self.campaign_id, approve_all=True, approved_by="chat"
                )
            else:
                ids = self._resolve(rest)
                if not ids:
                    return "Which ones? `approve all` or `approve 1 3` (run `show` first)."
                n = camp.approve(
                    s, campaign_id=self.campaign_id, message_ids=ids, approved_by="chat"
                )
        return f"Approved {n}. `send` when ready (or `send dry` to preview)."

    def _edit(self, rest: str) -> str:
        num, _, body = rest.partition(" ")
        if not num.isdigit() or not body.strip():
            return "Usage: edit <n> <new body>"
        idx = int(num)
        if not (1 <= idx <= len(self.listing)):
            return "Run `show` first, then edit by number."
        from azul.db.models import Message
        from azul.enums import ReviewDecision

        with session_scope() as s:
            m = s.get(Message, self.listing[idx - 1])
            if m is None:
                return "That draft is gone."
            m.human_edited_body = body.strip()
            m.review_decision = ReviewDecision.EDIT
        return f"Edited draft [{idx}]. Your edit is logged as a training signal."

    def _send(self, dry: bool) -> str:
        if self.campaign_id is None:
            return "Start a campaign first."
        with session_scope() as s:
            n = camp.send_approved(s, campaign_id=self.campaign_id, dry_run=dry)
        verb = "Would send" if dry else "Sent"
        return f"{verb} {n}. Then `sync` for replies, `report` for the number."

    def _sync(self) -> str:
        from datetime import UTC, datetime, timedelta

        from azul.connectors import get_channel
        from azul.memory import EpisodicMemory

        replies = get_channel().fetch_replies(datetime.now(tz=UTC) - timedelta(days=14))
        with session_scope() as s:
            mem = EpisodicMemory(s)
            recorded = sum(1 for r in replies if mem.ingest_reply(r) is not None)
        return f"Pulled {len(replies)} inbound, recorded {recorded}. (Stub channel returns none.)"

    def _report(self) -> str:
        if self.campaign_id is None:
            return "Start a campaign first."
        with session_scope() as s:
            r = camp.build_report(s, campaign_id=self.campaign_id)
        return (
            f"{r.campaign}: {r.sent} sent · {r.replied} replied · {r.meetings} meetings · "
            f"{r.bounced} bounced → REPLY RATE {r.reply_rate:.0%}"
        )


def run_chat() -> None:
    print("Azul — type `help`, or `quit` to leave.")  # noqa: T201
    session = ChatSession()
    while True:
        try:
            line = input("you ▸ ").strip()
        except (EOFError, KeyboardInterrupt):
            print()  # noqa: T201
            break
        if line.lower() in ("quit", "exit"):
            break
        reply = session.handle(line)
        if reply:
            print(f"azul ▸ {reply}")  # noqa: T201
