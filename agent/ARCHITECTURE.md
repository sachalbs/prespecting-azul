# Azul — architecture (état + cible) & challenges

> Document de référence. Carte précise de ce qu'est Azul, comment ça s'assemble,
> et où sont les vrais risques. Lis la **§7 (challenges)** en priorité.

---

## 0. La tension à trancher (avant tout)

Le brief fondateur dit : **« faible volume, haute qualité, anti-spray, la seule
métrique = le taux de réponse ».** Le nouveau cap dit : **« le plus gros logiciel
de prospection ».**

⚠️ **Ce sont deux entreprises différentes.** « Le plus gros » = volume, multi-canal,
data à l'échelle, intégrations CRM, délivrabilité industrielle, équipes. « Premium »
= peu de touches, ultra-perso, humain dans la boucle. Toute l'archi actuelle est
construite pour le **premium**. On peut viser grand — mais il faut **choisir le
chemin** (voir §8). Tout le reste du doc tient debout quel que soit le choix ; ce
qui change, c'est *où on investit ensuite*.

---

## 1. Le flux de bout en bout (cible produit)

```
ONBOARDING
  paie ──> bot chat (Telegram, puis WhatsApp) ──> "connecte ton Outlook" (OAuth) ──> essai

BOUCLE (par prospect, pilotée depuis le chat)
  liste/ICP
    ──> SOURCING      trouve + vérifie l'email (avant tout envoi)
    ──> RESEARCH      deep research -> 1 hook spécifique, non-évident
    ──> WRITING       message hyper-perso (playbook + mémoire) 
    ──> VALIDATION    brouillon envoyé dans le chat -> tap pour approuver/éditer
    ──> SEND          depuis la vraie boîte, espacé (jamais computer-use)
    ──> REPLIES       poll/webhook -> outcomes
    ──> FLYWHEEL      curator -> skills -> réinjecté dans le writer
    ──> RELANCE       1 follow-up auto pour les non-répondants
```

---

## 2. Carte des composants (précis)

| Brique | Rôle | Interface (swappable) | Impl actuelle | Cible « scale » |
|---|---|---|---|---|
| Orchestrateur | la boucle + état campagne | — (LangGraph) | LangGraph + `campaign.py` | + file d'attente + workers |
| Sourcing | trouver + vérifier l'email | `EmailVerifier` | Prospeo enrich / Hunter / stub | **data layer** (cf. §7.3) |
| Research | hook profond | `ResearchEngine` | Holo3 computer-use (Playwright) / stub | data/API > scraping |
| Writing | message perso | `Writer` | OpenAI-compat (Mistral/GLM/DeepSeek) + playbook | idem + A/B |
| Connecteur prospect | envoi + réponses | `Channel` | MS Graph (Outlook) send+poll / stub | + Gmail, multi-domaine |
| Canal opérateur | user ↔ Azul | (transport) | Telegram (long-poll/webhook) | + WhatsApp Cloud API officiel |
| Mémoire | se souvenir + apprendre | — | épisodique (recall) + procédurale (skills) + curator (Wilson) | + embeddings pgvector |
| Onboarding | connecter les comptes | — | OAuth auth-code + `ConnectedAccount` (par tenant) | + billing |
| DB | persistance + vecteurs | SQLAlchemy/Alembic | Postgres+pgvector (sqlite en dev) | + RLS multi-tenant |
| API | callbacks/webhooks | FastAPI | OAuth Outlook + reply webhook | + WhatsApp/Telegram webhooks |
| Surface | piloter Azul | `ChatSession` | CLI `chat` + Telegram | WhatsApp + NL via LLM |

**Principe** : chaque moteur externe est derrière une interface → on en change sans
refonte. Le moat n'est pas la techno, c'est **la donnée d'outcome + la qualité**.

---

## 3. Topologie de déploiement

```
Landing (Next.js) ─────────────> Vercel            (déjà en ligne)
Agent Azul (always-on worker) ─> Fly/Render        bot + pipeline + curator + FastAPI(OAuth/webhooks)
Postgres + pgvector ───────────> Neon/Supabase
```
Le serverless (Vercel) ne convient PAS à l'agent : long-poll + navigateur + envois
espacés = process persistant. Vercel = landing (+ éventuellement les callbacks).

---

## 4. Modèle de données

`tenants` · `connected_accounts` (OAuth par tenant) · `campaigns` ·
`campaign_prospects` · `prospects` · `research` · `messages` (+ relances via
`parent_message_id`/`step`, idempotent via `dedup_key`) · `outcomes` (le log
d'apprentissage) · `skills` (procédural, dé-identifié au niveau segment).
Tout porte `tenant_id` (RLS-ready).

---

## 5. Sécurité & conformité (état)

- Secrets en env uniquement ; jamais commités. ✅
- Patterns dé-identifiés au niveau segment ; pas de fuite cross-tenant. ✅
- ❌ **Manque pour un vrai SaaS EU** : RGPD (registre, opt-out/désinscription,
  base légale du démarchage B2B), CAN-SPAM, rétention, DPA. **À construire.**

---

## 6. État réel (build vs reste)

**Construit & testé** (pyright strict 0, ruff, **34 tests**) : tout le moteur
(sourcing→research→writing→send→replies), chat (CLI + Telegram), mémoire +
flywheel, relance, onboarding brick-1 (OAuth Outlook par tenant).
**Jamais tourné en live** (l'env cloud est allowlisté → 0 vrai appel externe,
0 vrai email, 0 vrai taux de réponse).
**Reste** : déployer (worker), valider les vraies formes API, WhatsApp officiel,
billing, conformité, et **le run réel qui prouve la thèse**.

---

## 7. CHALLENGES (on challenge tout)

1. **Positionnement (le plus important).** « Le plus gros » contredit « anti-spray
   faible volume ». Choisis (§8) — ça décide où va l'argent.
2. **Thèse non prouvée.** *La touche profonde convertit-elle assez ?* Zéro donnée
   réelle à ce jour. Tout le reste est secondaire tant que ce chiffre n'existe pas.
3. **Sourcing = le vrai moat manquant.** Trouver l'email *fiable* à l'échelle = une
   **data layer** (partenariats/API payantes). L'OSS est faible ici. Pour « le plus
   gros », **c'est LE sujet**, pas la rédaction.
4. **Research par navigateur (LinkedIn).** Fragile, anti-bot, bannissable, **ne
   scale pas**. À l'échelle → données/API, pas du scraping headless.
5. **Délivrabilité industrielle.** Domaines dédiés, warmup, rotation, SPF/DKIM/DMARC,
   bounce < 3 %. Discipline entière **non construite** ; « le plus gros » en dépend
   totalement (sinon spam-folder).
6. **Canal WhatsApp.** OSS (Baileys) = gris/bannissable ; officiel (tu es partenaire)
   = compliant mais setup. Telegram d'abord = pragmatique.
7. **Scalabilité technique.** 1 worker → file d'attente + workers horizontaux +
   idempotence concurrente + multi-région. Aujourd'hui : mono-process.
8. **Conformité (cf. §5).** Un SaaS de démarchage EU sans RGPD/opt-out = risque légal.
9. **Coût unitaire.** Deep research (navigateur + LLM) **par prospect** coûte cher ;
   à volume, l'économie doit tenir (research léger pour le tri, profond pour le top).
10. **Le moat dépend du volume.** Le flywheel n'apprend qu'avec des outcomes → tension
    directe avec « faible volume ». L'angle « gros » nourrit mieux le moat — mais voit §1.

---

## 8. Trois chemins (à choisir)

- **A — Premium (le brief).** ICP : founders/petites équipes. Moat : qualité +
  outcome data. Archi actuelle quasi suffisante. Risque : marché/prix plus petit.
- **B — Le plus gros (volume).** Multi-canal, **data layer** sourcing, délivrabilité
  industrielle, intégrations CRM, sièges équipe, conformité lourde. Archi : +data,
  +scale, +compliance. Risque : on devient un Apollo/Instantly — concurrence dure,
  et on perd le « anti-spray ».
- **C — Hybride (recommandé).** *Prouver A sur 25 réels → garder les rails B
  (interfaces déjà swappables) → scaler ce qui marche.* C'est littéralement la
  philosophie du brief : « archi qui scale sans refonte, mais build la tranche fine
  d'abord ». On ne ferme aucune porte, on dérisque dans le bon ordre.

**Prochaine action décisive, quel que soit A/B/C : le premier vrai chiffre.** Rien
ne se décide vraiment avant ça.
