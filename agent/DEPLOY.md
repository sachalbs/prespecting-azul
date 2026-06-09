# Azul — deployment architecture

## TL;DR
- **Landing** (Next.js) → **Vercel** (already live).
- **Azul agent** (bot + pipeline + OAuth callback) → **one small always-on worker**
  (Fly.io / Render / Railway). **Not** Vercel serverless.
- **Database** → managed **Postgres + pgvector** (Neon, Supabase, …).

## Why the agent is a worker, not serverless
The agent has three persistent/long-running needs that don't fit short, stateless
serverless functions:
1. **Telegram long-poll** bot = a process that stays connected (stateful sessions).
2. **Holo3 research** drives a **headless Chromium** (Playwright) per prospect.
3. **Sends are paced** over minutes/hours (deliverability), not a request/response.

Vercel is ideal for the landing and *could* host the OAuth callback as a function,
but the agent wants a worker. Keep them separate.

## Minimal beta footprint
- **1 worker** running:
  - `azul telegram-bot` — the operator chat (long-poll; no public URL needed).
  - the campaign pipeline + `azul learn` (curator), triggered from chat.
  - a small FastAPI (`azul.api`) for the OAuth callback + reply webhook (when wired).
- **1 Postgres** (pgvector). `uv run alembic upgrade head` once.
- Secrets via the host's env (never committed). See `.env.example`.

## Webhook vs long-poll (Telegram / WhatsApp)
- **Beta = long-poll** (`azul telegram-bot`): simplest, stateful, no public URL.
- **Prod = webhook**: needs a public URL **and** DB-backed session state (so a
  stateless function can resume a chat). `TelegramBot.handle_update` already backs
  both; persisting per-chat state is the work to switch.

## Connect-Outlook-from-chat (next brick)
Self-hosted OAuth (no Unipile): a hosted **authorization-code** flow on the worker's
FastAPI —
`/oauth/outlook/start?tenant=…` → Microsoft consent → `/oauth/outlook/callback`
stores a **per-tenant** refresh token (`ConnectedAccount`). The Telegram bot sends
the user the start link; on return, their trial can begin. Requires the redirect
URI registered in the Entra app.

## WhatsApp (later, official)
User is a WhatsApp Business partner → **official Cloud API** (`graph.facebook.com`),
no ban risk. Plugs into the same `handle_update` as Telegram.
