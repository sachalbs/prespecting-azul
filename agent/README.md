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
| Sourcing | `SOURCING_PROVIDER=waterfall` + `PROSPEO_API_KEY` / `HUNTER_API_KEY` / `DROPCONTACT_API_KEY` |
| Research | `RESEARCH_ENGINE=holo3` + `HOLO3_API_KEY` (+ base url)            |
| Writing  | `WRITER_PROVIDER=openai_compat` + `WRITER_BASE_URL` / `WRITER_MODEL` / `WRITER_API_KEY` |
| Sending  | `CHANNEL=unipile` + `UNIPILE_API_KEY` / `UNIPILE_DSN` / `UNIPILE_ACCOUNT_ID` |

Replies/bounces: run `uvicorn azul.api.webhooks:app` and point the Unipile
webhook at `POST /webhooks/replies`.

> The Holo3, Unipile and Prospeo/Dropcontact adapters are real skeletons with
> `TODO(*-docs)` markers where the exact request/response shape must be confirmed
> against each provider's docs before the first live send.

## Migrations & tests

```bash
uv run alembic upgrade head     # prod schema (enables pgvector on Postgres)
uv run pytest                   # unit + end-to-end on stubs
uv run ruff check . && uv run pyright
```
