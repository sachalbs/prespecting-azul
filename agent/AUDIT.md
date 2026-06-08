# Azul — project audit & debrief

_Snapshot of the `agent/` codebase. Honest state, risks, and the path to a real number._

## Verdict

The **product is built and coherent**: a chat-driven, memory-backed deep-research
SDR with clean swappable engines, a flywheel, and green quality gates. It has
**never run against a live API** (this environment is network-allowlisted and no
keys/list/mailbox-consent are wired), so the engineering is proven, but the
**reply-rate thesis is not** — that needs a local run. Net: ~1 ops setup + 1 local
run away from a real signal. The remaining risk is **operational and real-world
(LinkedIn bot-walls, provider response shapes), not architectural.**

## Metrics

| | |
|---|---|
| Source | 51 files · ~3,526 LOC |
| Tests | 9 files · 27 tests (logic + flows; externals mocked) |
| Gates | pyright **strict** 0 errors · ruff clean · 27 passing |
| LOC by module | orchestrator 720 · cli 582 · research 442 · sourcing 376 · db 318 · connectors 274 · writing 257 · memory 250 · api 57 |
| Open TODO markers | 2 (Dropcontact only — a deferred waterfall provider) |

## Maturity by module

| Module | State | Notes |
|---|---|---|
| `db` | ✅ solid | Typed SQLAlchemy 2.0, 8 tables, Alembic, sqlite↔Postgres portable; pgvector degrades on sqlite |
| `orchestrator` | ✅ solid | LangGraph pipeline + campaign lifecycle; idempotent, paced; **HITL gate via message status** (not yet a LangGraph interrupt) |
| `sourcing` | 🟡 real, unverified | Prospeo `enrich-person` per docs; Hunter ok; **Dropcontact stubbed**; free-tier email masking → RISKY |
| `research` | 🟡 real, unverified | Holo3 computer-use loop to spec (normalised coords, stealth); **never run live**; LinkedIn browse is the fragile bit |
| `writing` | 🟡 real, unverified | Playbook = system prompt; env-driven GLM/DeepSeek; stub for offline |
| `connectors` | 🟡 real, unverified | MS Graph send (draft+send) + reply polling; MSAL device-code; bounce detection heuristic |
| `memory` | ✅ built | Episodic (relationship recall) + procedural (skills) + curator + Wilson eval; learns from whatever outcomes exist |
| `cli` | ✅ solid | `chat` (product surface), run/approve/send/report, `learn`, `follow-up`, `doctor`, `auth-email`, `linkedin-login` |
| `api` | 🟡 minimal | FastAPI reply webhook (polling is the primary path in Jalon 0) |

Legend: ✅ done & tested · 🟡 implemented but not exercised against the live API.

## Strengths

- **Clean seams.** Every engine sits behind an interface (`EmailVerifier`,
  `ResearchEngine`, `Writer`, `Channel`) chosen by env — stub↔live is a config flip.
- **Flywheel-ready data model from day one**: multi-tenant columns, the `outcomes`
  learning log, segment-level de-identified `skills`, idempotent `dedup_key`,
  follow-ups as child messages.
- **Disciplined eval**: Wilson lower bound stops tiny samples from being trusted
  (anti-drift to slop) — the brief's key concern, honoured.
- **Honest offline mode**: stubs let the whole loop run and emit a number with zero
  keys; the same code path goes live by setting `.env`.
- **Quality bar held throughout**: strict pyright, ruff, tests on every change.

## Risks & gaps (ranked)

1. **Never run live (highest).** All external paths are mock-tested only. First
   real call will surface response-shape mismatches (Holo actions, Graph ids,
   Prospeo fields). Mitigation in place: each adapter logs raw payloads on failure.
2. **Holo on LinkedIn from a datacenter IP** — bot-wall / account-ban risk. Stealth
   added, but plan B (web/company + Prospeo dossier) should be the default if it
   gets blocked.
3. **Prospeo free tier may mask emails** → not sendable (surfaced as RISKY). A paid
   credit is likely needed to reveal-and-send.
4. **Reply attribution is heuristic** (match by sender address; bounce by
   sender/subject). Fine at low volume; should move to threading/`conversationId`
   matching for robustness.
5. **Flywheel learns from simulated outcomes** until a real run; samples at 25
   prospects are tiny (the min-sample gate guards against acting on noise).
6. **Multi-tenant not enforced** — `tenant_id` is present everywhere (RLS-ready) but
   no row-level security is active yet. Single-tenant in practice.
7. **No CI** — gates run locally; a GitHub Actions workflow would enforce them on push.
8. **Secret hygiene** — env-only (good), but the Holo key was shared in chat;
   **rotate it**.

## Security & privacy

- Secrets in env / `.env` only; nothing in code or git (verified).
- Cross-customer patterns are de-identified at the **segment** level in `skills`
  (no per-lead data, no cross-tenant leakage) — privacy guard respected.
- Sending is always an API call from the real mailbox; **never computer-use**
  (computer-use is research-only, on public/owned sessions).

## Recommended next moves (after a real number)

1. **Run the beta** (local): keys + playbook + 25-prospect list → first real reply rate.
2. Harden reply attribution (thread/`conversationId`); real email threading for follow-ups.
3. Graduate the HITL gate to a LangGraph `interrupt()` + the WhatsApp/Slack chat hook.
4. Embeddings for `skills` (pgvector) once an embedder is available → semantic recall.
5. CI (GitHub Actions): pyright + ruff + pytest on every push.
6. Real multi-tenant (Postgres RLS) when a second tenant appears.

## How to verify locally

```bash
cd agent && uv sync --extra dev
uv run ruff check . && uv run pyright && uv run pytest   # gates
uv run azul init-db && uv run azul chat                  # the product, stub mode
```
Real run: see `SETUP_BETA.md`.
