"""`azul chat` — the product surface: manage Azul like an employee, from chat.

A local conversational console that drives the same campaign engine. The
WhatsApp/Slack hook (via the Channel) plugs into this exact surface later; the
intent parser can graduate to the Writer/LLM. Kept deterministic for now so it
runs and is testable without any keys.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from azul.cli.intent import interpret
from azul.config import get_settings
from azul.db.session import session_scope
from azul.orchestrator import campaign as camp

HELP = """\
I'm Azul. Manage me like an SDR. Commands:
  connect                           connect your Outlook (one click) — sends go from your box
  discover <ICP brief>              find prospects from a description (then `list`, `approve-list`)
  list                              show the discovered leads
  approve-list                      validate the list -> find emails + write drafts
  campaign <name> from <file.csv>   start from a CSV instead (source -> research -> draft)
  show                              show the drafts waiting for your approval
  approve all | approve 1 3         approve drafts (numbers from `show`)
  edit <n> <new body>               replace a draft's body (your edit is logged)
  send [dry]                        send approved mail (paced, from your mailbox)
  sync                              pull replies/bounces into outcomes
  report                            the number that matters: reply rate
  follow-up                         draft a relance for everyone who didn't reply
  status                            quick state of the current campaign
  learn                             mine outcomes into what works (the flywheel)
  memory                            show what I've learned by segment
  help · quit
"""


@dataclass
class ChatSession:
    tenant: str = "me"
    sender: str | None = None
    campaign_id: uuid.UUID | None = None
    listing: list[uuid.UUID] = field(default_factory=list)

    def handle(self, line: str, _interpreted: bool = False) -> str:
        line = line.strip()
        if not line:
            return ""
        cmd, _, rest = line.partition(" ")
        out = self._dispatch(cmd.lower(), rest.strip())
        if out is not None:
            return out
        # Unknown command: try the NL intent parser (Writer LLM), then dispatch once.
        if not _interpreted:
            translated = interpret(line)
            if translated:
                # A REAL send must never fire off an LLM's interpretation of free
                # text — require the user to type the explicit command themselves.
                t_cmd, _, t_rest = translated.partition(" ")
                if t_cmd == "send" and "dry" not in t_rest.lower():
                    return (
                        "J'ai compris `send` (envoi réel depuis ta boîte). Par sécurité, "
                        "tape `send` toi-même pour confirmer — ou `send dry` pour un aperçu."
                    )
                return self.handle(translated, _interpreted=True)
        return "Didn't catch that. Type `help`."

    def _dispatch(self, cmd: str, rest: str) -> str | None:
        if cmd in ("help", "?"):
            return HELP
        if cmd == "connect":
            return self._connect()
        if cmd == "discover":
            return self._discover(rest)
        if cmd in ("list", "leads", "show-list"):
            return self._list_leads()
        if cmd in ("approve-list", "go-list"):
            return self._approve_list()
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
        if cmd == "status":
            return self._status()
        if cmd in ("follow-up", "followup", "relance"):
            return self._followup()
        if cmd == "learn":
            return self._learn()
        if cmd in ("memory", "learned", "brain"):
            return self._memory()
        return None

    # ── commands ──────────────────────────────────────────────────────────────
    def _connect(self) -> str:
        base = get_settings().public_base_url.rstrip("/")
        return (
            "Connecte ton Outlook (un clic, ~30 s) puis reviens : "
            f"{base}/oauth/outlook/start?tenant={self.tenant}"
        )

    def _discover(self, rest: str) -> str:
        if not rest:
            return "Usage: discover <brief ICP> (ex: fondateurs d'agences growth FR, 5-30)"
        with session_scope() as s:
            c = camp.discover_campaign(s, tenant_slug=self.tenant, name=rest[:60], icp_brief=rest)
            self.campaign_id = c.id
            n = len(camp.list_leads(s, c.id))
        return f"Trouvé {n} leads. `list` pour voir, `approve-list` pour la suite."

    def _list_leads(self) -> str:
        if self.campaign_id is None:
            return "Lance d'abord `discover <brief ICP>`."
        with session_scope() as s:
            leads = camp.list_leads(s, self.campaign_id)
        if not leads:
            return "Aucun lead découvert."
        lines = [
            f"[{i}] {ld.get('full_name')} — {ld.get('company') or '-'} "
            f"({ld.get('company_domain') or '-'})"
            for i, ld in enumerate(leads, 1)
        ]
        return "\n".join(lines) + "\n\n`approve-list` → emails + messages."

    def _approve_list(self) -> str:
        if self.campaign_id is None:
            return "Lance d'abord `discover <brief ICP>`."
        with session_scope() as s:
            n = camp.approve_list(s, campaign_id=self.campaign_id, sender_name=self.sender)
        return f"Liste validée → {n} brouillon(s) prêts. `show` pour relire, puis `approve`/`send`."

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

    def _status(self) -> str:
        if self.campaign_id is None:
            return "No campaign yet. Start one: campaign <name> from <file.csv>"
        with session_scope() as s:
            r = camp.build_report(s, campaign_id=self.campaign_id)
            awaiting = len(camp.list_drafts(s, self.campaign_id))
        return (
            f"{r.campaign}: {r.drafted} drafted · {awaiting} awaiting approval · "
            f"{r.sent} sent · {r.replied} replied."
        )

    def _followup(self) -> str:
        if self.campaign_id is None:
            return "Start a campaign first."
        with session_scope() as s:
            n = camp.generate_followups(
                s, campaign_id=self.campaign_id, sender_name=self.sender
            )
        return f"Drafted {n} follow-up(s) for non-repliers. `show`, then approve/send."

    def _learn(self) -> str:
        from azul.memory.flywheel import run_curator

        with session_scope() as s:
            n = run_curator(s)
        return f"Learned/updated {n} pattern(s) from outcomes. Ask `memory` to see them."

    def _memory(self) -> str:
        from sqlalchemy import select

        from azul.db.models import Skill

        with session_scope() as s:
            skills = list(s.scalars(select(Skill).order_by(Skill.eval_score.desc())))[:8]
            lines = [
                f"  {sk.segment}/{sk.pattern}: {(sk.win_rate or 0):.0%} over "
                f"{sk.sample_size} (score {(sk.eval_score or 0):.2f})"
                for sk in skills
            ]
        if not lines:
            return "Nothing learned yet. Run a campaign, get outcomes, then `learn`."
        return "What I've learned so far:\n" + "\n".join(lines)


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
