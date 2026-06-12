# Azul — setup envoi Outlook (MS Graph, device-code)

Procédure exacte pour brancher l'envoi réel depuis **scipion.beylouni@outlook.com**.
À faire **en local** (l'auth device-code exige un navigateur et une action humaine
sur microsoft.com/devicelogin — impossible depuis l'environnement cloud).

L'app Azure est **déjà configurée et validée** (réutilisée de Lokia) :

| Quoi | Valeur |
|---|---|
| Client ID | `64818738-5975-4e2e-97df-fef2e483f05e` |
| Flux | Device-code (public client flows activés) |
| Permissions déléguées | `Mail.Send`, `Mail.Read`, `offline_access`, `User.Read` |
| Endpoint | `https://login.microsoftonline.com/common` |
| Secret / tenant | Aucun (public client, pas de client_secret, pas de tenant_id) |

Rien à toucher côté Azure. Tout se passe en CLI, dans `agent/`.

## 1. Mettre le code et l'env à jour

```bash
cd agent
git pull
uv sync --extra dev
```

## 2. Le `.env`

Le `.env` est **gitignoré** (jamais commité) : il n'arrive pas par `git pull`,
il faut le créer/compléter localement. Si tu pars de zéro :

```bash
cp .env.example .env
```

Puis vérifie/ajuste ces lignes (le reste peut rester en stub pour ce setup —
les autres adapters live, c'est `SETUP_BETA.md`) :

```env
CHANNEL=graph
GRAPH_CLIENT_ID=64818738-5975-4e2e-97df-fef2e483f05e
GRAPH_AUTHORITY=https://login.microsoftonline.com/common
GRAPH_TOKEN_CACHE=.msal_cache.bin
```

Et initialise la base si ce n'est pas déjà fait (sinon `doctor` rouspète) :

```bash
uv run azul init-db
```

## 3. L'auth — une seule fois

```bash
uv run azul auth-email
```

Ce qui se passe, dans l'ordre :

1. La commande affiche un message du type :
   > To sign in, use a web browser to open the page
   > **https://microsoft.com/devicelogin** and enter the code **XXXXXXXXX**
   > to authenticate.
2. **Copie le code**, ouvre https://microsoft.com/devicelogin dans ton navigateur.
3. Colle le code, puis connecte-toi avec **scipion.beylouni@outlook.com**
   (le compte qui enverra les emails — pas un autre).
4. Microsoft affiche l'écran de consentement (Mail.Send, Mail.Read…) → **Accepte**.
5. La commande (qui attendait pendant ce temps) se termine sur :
   > Email auth complete; token cached.

Résultat : le fichier **`.msal_cache.bin`** est créé dans `agent/`. Il contient
le refresh token (`offline_access`) — tous les envois et polls suivants sont
**silencieux** : aucun re-login ne sera demandé, le token est rafraîchi tout seul.

⚠️ `.msal_cache.bin` = l'accès à la boîte mail. Il est dans `.gitignore` (avec
`.env`) : **ne jamais le committer, ne jamais le partager**. Pour révoquer :
supprimer le fichier + retirer l'app « Azul » sur
https://account.live.com/consent/Manage.

## 4. Vérifier : `doctor` vert

```bash
uv run azul doctor
```

Ce que tu dois voir côté Graph (checks **réels**, pas juste l'env) :

```
  OK  GRAPH_CLIENT_ID
  OK  Graph token cached (.msal_cache.bin)

Live checks (real calls):
  OK   DB — sqlite:///azul.db
  OK   Graph /me — scipion.beylouni@outlook.com
  OK   Mail.Send scope — Mail.Read Mail.Send User.Read ...
```

Ce que ça prouve : le token en cache se rafraîchit en silence
(`acquire_token_silent`), `GET /me` répond avec la bonne boîte, et le scope
`Mail.Send` est bien dans le token. Si l'un des trois manque → §6.

Notes de lecture :
- Les lignes **SPF/DKIM/DMARC** qui suivent concernent le domaine `outlook.com`,
  géré par Microsoft : informatif, pas bloquant, rien à faire.
- Relance `uv run azul doctor` une 2e fois : il doit repasser vert **sans**
  redemander de login — c'est la preuve que le cache + `offline_access` marchent.

## 5. Dernier contrôle avant tout envoi réel

1. `doctor` 100% vert côté Graph (les 3 lignes ci-dessus).
2. `Graph /me` affiche bien **scipion.beylouni@outlook.com** (pas un autre compte).
3. Optionnel mais recommandé — un (1) vrai mail de probe vers mail-tester :
   va sur https://www.mail-tester.com, copie l'adresse `test-...@srv1.mail-tester.com`, puis :
   ```bash
   uv run azul deliverability-check test-xxxxx@srv1.mail-tester.com
   ```
   et lis le score sur la page. C'est le seul envoi avant le run ; tout le reste
   passe par `review` → `approve` → `send-approved` (pacé, idempotent, plafonné
   à `DAILY_SEND_CAP=25`).

## 6. Dépannage

| Symptôme | Cause / remède |
|---|---|
| `GRAPH_CLIENT_ID is required for CHANNEL=graph` | Le `.env` n'est pas lu : lance les commandes **depuis `agent/`** (le `.env` et `.msal_cache.bin` sont relatifs au dossier courant). |
| `No cached Graph token — run azul auth-email` | Pas encore authentifié (ou `.msal_cache.bin` supprimé) → §3. |
| Erreur AADSTS sur le type de compte au device-code | Essaie `GRAPH_AUTHORITY=https://login.microsoftonline.com/consumers` (tenant des comptes perso) puis relance `azul auth-email`. |
| `AADSTS7000218` (client_secret attendu) | « Allow public client flows » a été désactivé côté Azure → le réactiver (Authentication → Advanced). |
| `consent lacks Mail.Send — re-run azul auth-email` | Consentement incomplet : supprime `.msal_cache.bin`, relance `azul auth-email` et accepte tout l'écran de consentement. |
| `Graph /me FAIL … token may be stale` | Supprime `.msal_cache.bin` et refais §3 (re-consentement en 30 s). |
