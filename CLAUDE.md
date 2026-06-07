# Azul — autonomous prospecting agent (deep-research SDR)

> Global context + working brief. This file is the source of truth for *what we're
> building and why*. Code for the agent lives in [`/agent`](./agent); the marketing
> landing page (Next.js) lives at the repo root and is deployed to Vercel.

## Mission

Azul is an AI SDR **driven from chat** (no dashboard). For each prospect it runs
**deep research**, writes a **hyper-personalised** message, submits it for **human
approval**, sends it **from the user's real mailbox**, tracks replies, follows up,
and **learns from every outcome**.

Low volume, high quality. Anti-spray, anti-template, anti-slop. Managed **like an
employee, not a piece of software**. The only metric that matters: **reply rate**.

## Engineering philosophy (respect absolutely)

- **The thesis isn't proven yet.** Open question: does the deep touch convert
  *enough*? So the first milestone is **not "the full product"** — it's the **thin
  slice** that produces a real reply rate on ~25 prospects. Prove, then scale.
- **Sound foundations = architecture that scales without a rewrite, not concrete
  poured too early.** Clean module boundaries and a flywheel-ready, multi-tenant
  data model from day one — but only **build** the thin slice first.
- **Every external engine is a commodity behind an interface.** Research (Holo3),
  models, connector: abstracted, swappable. The moat isn't the tech — it's the
  **outcome data + per-touch quality**.
- **Log everything from day one.** Each touch and its outcome
  (`segment × angle × timing → result`) is the flywheel's raw material. The outcome
  schema is sacred.

## What we are NOT building (anti-scope)

- ❌ No home-grown email database (rented via API).
- ❌ No dashboard (the interface is chat).
- ❌ No full autonomy on day one (human approval required; graduate with trust).
- ❌ No full flywheel logic before real data (lay the *schema*, not the curator/eval).
- ❌ No self-hosted GPU in v0 (Holo API; self-host only at high volume).

## Locked architecture

| Brick | Choice | Note |
|---|---|---|
| Orchestrator | **LangGraph** (Python) | We own the loop; HITL-ready |
| Sourcing + emails | Waterfall API: Prospeo → Hunter → Dropcontact | Verify **before** any send, bounce < 3% |
| Deep research | Holo3 via API, behind `ResearchEngine` | Swappable (Qwen3-VL) |
| Writing | Strong text model (GLM-5.1 / DeepSeek V4) behind `Writer` | OpenAI-compatible, env-driven; the one call we pay quality for |
| Connector / send | Unipile (Outlook + Gmail + LinkedIn + WhatsApp) | OAuth + reply webhooks. Send = API call from the real mailbox, **never** computer-use |
| Human approval | Chat (WhatsApp/Slack) via Unipile | Tap to approve (CLI stand-in in Jalon 0) |
| Memory / flywheel | **Postgres + pgvector** (SQLAlchemy 2.0 + Alembic) | **episodic** (what happened) / **procedural** (skills) split |

### Decisions taken
- Orchestrator: **LangGraph from the start** (state machine + interrupt for HITL).
- DB layer: **SQLAlchemy 2.0 + Alembic** (pgvector in prod; sqlite fallback for zero-infra runs).
- Writer: **env-driven OpenAI-compatible client** — GLM-5.1 *or* DeepSeek V4 drop in
  via `WRITER_BASE_URL`/`WRITER_MODEL`/`WRITER_API_KEY` (model TBD).
- Reference studied: `MaxKmet/idea-validation-agents` (cloned read-only) — its
  persistent `memory/` + episodic/skills split informed `azul/memory`.

## Modules (`/agent/src/azul`)

```
orchestrator   the control loop + a campaign's state (LangGraph)
sourcing       waterfall APIs, find + verify email
research       ResearchEngine interface + Holo3 adapter (+ stub)
writing        Writer interface + text-model adapter + prompts (+ stub)
connectors     Channel interface + Unipile adapter (send, sync replies) (+ stub)
memory         episodic store, procedural store (skills), curator/eval stubs
db             schema, migrations
api            internal endpoints (reply webhook)
cli            run a campaign, read results
```

## Data model (flywheel + multi-tenant from the start)

`tenants`, `campaigns`, `campaign_prospects`, `prospects`, `research`, `messages`,
`outcomes` (**the learning log**), `skills` (procedural, filled later). Every table
carries `tenant_id` (RLS-ready). Human approval + edits are captured on `messages`
(an edit is a training signal). Follow-ups = child messages (`parent_message_id` +
`step`). Sends are idempotent (`dedup_key` unique). Cross-customer patterns are
de-identified at the **segment** level — never leak leads across tenants.

## Jalon 0 — the thin slice (BUILT)

CLI: `run-campaign` (CSV → verify → research → write drafts) → `review` →
`approve` (the human tap) → `send-approved` (paced, idempotent) → replies via
webhook → `report` (reply rate). Runs today in **stub mode** (no keys, sqlite) and
emits a number; swap stubs for live adapters via `.env`. See [`agent/README.md`](./agent/README.md).

**No flywheel, no real multi-tenant, no autonomy** — but schema + interfaces are in
place so the next milestones slot in without a rewrite.

## Next milestones (sketched — DO NOT build until Jalon 0 produces a real number)

1. Chat hook (Unipile WhatsApp/Slack) for approval.
2. Curator + eval harness (graded by real reply rate; anti-drift to slop).
3. Real multi-tenant + cross-customer pooling at segment level (privacy guards).
4. Coupled loops (targeting / research / message / timing).
5. Graduation to partial autonomy as trust grows.

## Engineering standards

- Python, strict typing (pyright). Tests on logic (mock external APIs).
- Secrets in env vars, **never** in code.
- Every external engine behind an interface → swappable.
- Observability: log every touch + outcome; the flywheel depends on it.
- **Idempotent sends** (never double-send). Rate-limit / space sends (deliverability).
