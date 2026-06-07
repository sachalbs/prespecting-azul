# Azul — agent (Jalon 0)

Autonomous deep-research SDR. Jalon 0 is the **thin slice**: take ~25 prospects
through `source → research → write → human approval → send → outcome → report`
and emit a **real reply rate**. No flywheel, no real multi-tenant, no autonomy
yet — but the schema and interfaces are in place so later milestones slot in
without a rewrite.

## Layout

```
src/azul/
  config.py        settings (env / .env), typed
  orchestrator/    the loop — LangGraph pipeline + campaign lifecycle
  sourcing/        EmailVerifier: stub | waterfall (Prospeo→Hunter→Dropcontact)
  research/        ResearchEngine: stub | Holo3
  writing/         Writer: stub | OpenAI-compatible (GLM-5.1 / DeepSeek V4)
  connectors/      Channel: stub | Unipile (send + reply webhook)
  memory/          episodic (outcomes) + procedural (skills, stub) + flywheel stubs
  db/              SQLAlchemy models, portable types, session
  api/             reply webhook (FastAPI)
  cli/             the `azul` command
migrations/        Alembic
tests/             pytest (external APIs mocked via stubs)
```

Every external engine sits behind an interface and is chosen by env, so swapping
a backend is a config change, never a code change.

## Quickstart (stub mode — runs today, zero infra)

```bash
cd agent
uv sync --extra dev
cp .env.example .env          # defaults are sqlite + stub: no keys needed

uv run azul init-db
uv run azul run-campaign --tenant acme --name "Q1 outbound" \
    --list data/prospects.sample.csv --sender "You"
uv run azul review   --campaign "Q1 outbound"
uv run azul approve  --campaign "Q1 outbound" --all
uv run azul send-approved   --campaign "Q1 outbound"
uv run azul simulate-replies --campaign "Q1 outbound"   # stub-only
uv run azul report   --campaign "Q1 outbound"
```

`report` prints the number that matters: **reply rate**.

## Going live

Flip adapters in `.env` and provide the keys:

| Concern  | Env to set                                                        |
|----------|-------------------------------------------------------------------|
| Database | `DATABASE_URL=postgresql+psycopg://…` (Postgres 16 + pgvector)    |
| Sourcing | `SOURCING_PROVIDER=prospeo` + `PROSPEO_API_KEY` (enrich = find+verify+dossier) |
| Research | `RESEARCH_ENGINE=holo3` + `HAI_API_KEY` (computer-use; browses with `LINKEDIN_STORAGE_STATE`) |
| Writing  | `WRITER_PROVIDER=openai_compat` + `WRITER_BASE_URL` / `WRITER_MODEL` / `WRITER_API_KEY` + `WRITER_PLAYBOOK_PATH` |
| Sending  | `CHANNEL=graph` + `GRAPH_CLIENT_ID` (Outlook via MS Graph)        |

> ⚠️ Real run needs egress to these hosts. In Claude Code on the web the network
> is allowlisted — run the real campaign **locally**, or add the hosts to the
> environment's network policy.

### Real run (locally), email-only

```bash
playwright install chromium                 # one-time, for Holo research
uv run azul auth-email                       # one-time MS Graph device-code consent
uv run azul linkedin-login                   # one-time: log in, saves the session for Holo
uv run azul run-campaign --tenant you --name "Q1" --list prospects.csv --sender "You"
uv run azul review  --campaign "Q1"
uv run azul approve --campaign "Q1" --all    # or per --message <id>
uv run azul send-approved --campaign "Q1"    # paced, idempotent, from your real mailbox
uv run azul sync-replies --campaign "Q1"     # poll Outlook -> outcomes
uv run azul report  --campaign "Q1"          # the real reply rate
```

> Holo3's action schema in `research/holo3.py` is marked `TODO(holo-guide)` — confirm
> against the official agent-loop guide before the first research run.

## Migrations & tests

```bash
uv run alembic upgrade head     # prod schema (enables pgvector on Postgres)
uv run pytest                   # unit + end-to-end (HTTP mocked, no network)
uv run ruff check . && uv run pyright
```
