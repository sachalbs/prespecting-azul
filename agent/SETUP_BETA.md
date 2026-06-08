# Azul — runbook beta (premier vrai run)

But : un **vrai taux de réponse** sur 5 puis 25 prospects, email-only, validation
humaine, depuis ta vraie boîte. Tout le code est prêt et mock-testé ; il reste le
**setup ops** (ci-dessous) + un run **en local** (cet environnement cloud est
allowlisté, les APIs externes y sont bloquées).

## 0. Prérequis
- Python 3.11+, `uv`, et `playwright install chromium`
- Une boîte Outlook (l'envoi part de là)
- Clés : Prospeo, Holo (`HAI_API_KEY`), un modèle d'écriture (GLM **ou** DeepSeek)
- `AZUL_COLD_OUTREACH_PLAYBOOK.md` à la racine (cerveau du writer)
- Un CSV de prospects : `full_name, company, company_domain, title, segment`

## 1. App Microsoft (pour envoyer via Graph)
1. entra.microsoft.com → **App registrations** → **New registration**
2. Nom « Azul » ; comptes : *Personal Microsoft accounts* (ou « any org + personal ») → **Register**
3. Copie **Application (client) ID** → `GRAPH_CLIENT_ID`
4. **Authentication** → Advanced → **Allow public client flows = Yes** → Save (requis pour le device-code)
5. **API permissions** → Add → Microsoft Graph → **Delegated** → `Mail.Send`, `Mail.Read`, `User.Read` → Add
   (compte perso + delegated = pas de consent admin nécessaire)

## 2. .env
```bash
cd agent && cp .env.example .env
```
Mets les clés et **passe les 4 adapters en live** :
```
SOURCING_PROVIDER=prospeo
RESEARCH_ENGINE=holo3
WRITER_PROVIDER=openai_compat
CHANNEL=graph

PROSPEO_API_KEY=...
HAI_API_KEY=...
WRITER_BASE_URL=...     # GLM ou DeepSeek (OpenAI-compatible)
WRITER_MODEL=...
WRITER_API_KEY=...
GRAPH_CLIENT_ID=...
LINKEDIN_STORAGE_STATE=.linkedin_state.json
```
(DB : sqlite par défaut suffit pour la beta ; Postgres optionnel.)

## 3. Auth one-time
```bash
uv sync --extra dev && playwright install chromium
uv run azul auth-email        # consent Microsoft (device code)
uv run azul linkedin-login    # login LinkedIn -> session pour Holo
uv run azul doctor            # tout doit afficher "OK"
```

## 4. Dry-run sur 5
```bash
uv run azul run-campaign --tenant you --name dry5 --list five.csv --sender "Sacha"
uv run azul review        --campaign dry5
uv run azul approve       --campaign dry5 --all
uv run azul send-approved --campaign dry5 --dry-run   # inspecte, n'envoie pas
uv run azul send-approved --campaign dry5             # vrai envoi, espacé
uv run azul sync-replies  --campaign dry5
uv run azul report        --campaign dry5
```

## 5. Si ça casse au premier appel réel
Les adapters logguent l'échec + le payload brut (`holo_parse_failed`,
`graph_send_failed`, `Prospeo ...`). **Colle-moi ces lignes** → je corrige la vraie
forme (surtout Holo) en 1-2 itérations. Quand les 5 passent propre → relance sur 25.

## Risques connus
- **Holo sur LinkedIn depuis ton IP** : bot-wall/ban possible (point le plus fragile).
  Plan B déjà câblé : Holo sur web/société + dossier Prospeo.
- **Prospeo free tier** peut masquer l'email → marqué RISKY, non envoyé (crédit pour révéler).
- **Délivrabilité** : ≤ 5–10 envois/jour espacés ; c'est ta réputation de domaine.
