# Azul — project audit & debrief

_Current state of the `agent/` codebase. Read §1 (verdict) and §6 (risks)._

## 1. Verdict

Azul is now a **chat-driven, deep-research SDR with prospect discovery, two human
gates, episodic + procedural memory, a learning flywheel, and self-serve Outlook
onboarding** — all behind clean swappable interfaces, with green quality gates.
It has **never run against a live API** (this environment is network-allowlisted;
no keys/list/mailbox-consent wired), so the **engineering is proven, the reply-rate
thesis is not**. One search provider + keys + a real run separate us from the first
real number. Remaining risk is **operational and real-world, not architectural.**

## 2. Metrics

| | |
|---|---|
| Source | 60 files · ~4,095 LOC |
| Tests | 37 (logic + flows; externals mocked) · pyright **strict** 0 · ruff clean |
| Commits (this build) | 18 |
| LOC by module | orchestrator 795 · cli 644 · research 523 · sourcing 376 · connectors 361 · db 334 · writing 257 · memory 250 · discovery 122 · chatops 85 · api 81 |
| Open TODO | 2 (Dropcontact, a deferred provider) |
| Docs | README · V0 · SETUP_BETA · DEPLOY · ARCHITECTURE · AUDIT |

## 3. What was built (inventory)

- **Engine** (Jalon 0): source → research → write → approve → send → outcome → report, idempotent + paced.
- **Discovery**: ICP brief → leads (interface + stub; web-search skeleton) with a **list-approval gate**.
- **Sourcing**: Prospeo `enrich-person` (find + verify + dossier); Hunter; Dropcontact stub.
- **Research**: `dossier` (Prospeo-only, robust, v0), `holo3` (computer-use, premium), stub.
- **Writing**: playbook-as-system-prompt, OpenAI-compatible (Mistral / Gemini Flash / DeepSeek), stub.
- **Connector**: MS Graph (Outlook) send + reply polling; device-code **and** auth-code OAuth.
- **Operator chat**: `ChatSession` (CLI + **Telegram**); NL intent via the Writer LLM; per-chat tenant.
- **Memory + flywheel**: episodic `recall` (per person) + procedural `skills` + curator (Wilson eval).
- **Follow-ups**: one relance per non-replier (child message).
- **Onboarding**: per-tenant OAuth (`ConnectedAccount`), `/oauth/outlook/start|callback`, chat `connect`.
- **Ops**: `doctor` preflight, Alembic, sqlite↔Postgres portability.

## 4. The flow (with the two human gates)

```
discover (ICP brief) ──> [GATE 1: tu valides la liste] ──> Prospeo (email vérifié)
  ──> research (dossier) ──> write (Gemini/Mistral + playbook)
  ──> [GATE 2: tu valides les drafts] ──> send (Outlook) ──> outcomes ──> flywheel
```

## 5. Maturity by module

| Module | État |
|---|---|
| db · orchestrator · memory · cli · chatops · api | ✅ solides & testés |
| sourcing (Prospeo) · connectors (Graph) · writing (OpenAI-compat) · onboarding OAuth | 🟡 réels, **jamais exercés en live** (formes à valider au 1er appel) |
| discovery (websearch) · research (holo3) | 🟠 **squelettes** — discovery a besoin d'un fournisseur de search ; holo3 du guide + un run local |

## 6. Risks (ranked)

1. **Never run live (highest).** All external paths mock-tested only; first real call will surface shape mismatches (each adapter logs raw payloads on failure).
2. **Discovery sans data-provider = le maillon faible.** Web-search + extraction est moins fiable qu'Apollo/Lusha ; qualité + quantité de leads à prouver.
3. **Thèse non prouvée.** Zéro vrai taux de réponse à ce jour.
4. **Prospeo free tier peut masquer l'email** → non envoyable (marqué RISKY).
5. **Délivrabilité à l'échelle** (domaines/warmup/DMARC) non construite — clé si on scale.
6. **Attribution des réponses heuristique** (par expéditeur) — à durcir (threading).
7. **Conformité** (RGPD/opt-out/désinscription) non construite — requise pour un SaaS EU.
8. **Multi-tenant** : `tenant_id` partout (RLS-ready) mais RLS pas actif ; pas de CI.
9. **Secret** : la clé Holo + le token Telegram ont transité en clair dans le chat → **à révoquer**.

## 7. What's left (not more product — ops + 1 brick)

1. **1 brick de code** : brancher la découverte réelle à un fournisseur de search (Serper/Brave).
2. **Tes clés** (Prospeo, Gemini/Mistral, app Outlook) + `azul connect`/`auth-email`.
3. **Le faire tourner** sur une machine ouverte (ton ordi / un worker) → **le premier vrai chiffre**.

## 8. Verify locally
```bash
cd agent && uv sync --extra dev
uv run ruff check . && uv run pyright && uv run pytest   # gates
uv run azul init-db && uv run azul chat                  # le produit, en stub
```
Run réel : `SETUP_BETA.md` · v0 : `V0.md` · archi : `ARCHITECTURE.md`.
