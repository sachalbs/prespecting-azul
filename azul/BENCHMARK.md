# Benchmarks humains

> **Le moteur est `agent/`. La source de vérité des envois est la table
> `outcomes`. Ce dossier = benchmarks humains et notes opérateur.**

Ce fichier isole les références de comparaison externes au moteur. Ces chiffres
ne sont **jamais** des performances d'Azul et ne se cumulent jamais avec elles :
ils fixent la barre à battre.

## Benchmark 1 — campagne Apollo manuelle pré-Azul (experts-comptables)

Source : compte Apollo personnel de Sacha, lu le 2026-06-12 via le connecteur
MCP Apollo (`apollo_emailer_campaigns_search`, `apollo_email_accounts_index`).
Prospection menée à la main, boîte d'envoi `sachalbs@outlook.com` (domaine
gratuit, Exchange), avant toute existence d'Azul.

- Séquence `comptables` (2026-01-18 → 2026-04-28, 3 étapes, générique, sans
  segment ni déclencheur, aucun A/B test) : 423 envoyés, 418 délivrés,
  5 hard bounces (1,2 %), **24 réponses (5,7 %)**, 3 démos (0,7 %).
  Apollo la classait `is_performing_poorly`, les 3 étapes sous-performantes.
- Séquence `GOOGLE FORM` (sept. 2025) : 75 délivrés, 0 réponse, abandonnée.

### Ce que ce benchmark apprend

- **La barre à battre est 5,7 %** : c'est ce que fait un templé 3 étapes sans
  personnalisation sur ce marché. Si le deep touch d'Azul ne bat pas nettement
  ce chiffre sur son premier batch (~25 prospects, cf. Jalon 0), la thèse
  n'est pas validée.
- Le CTA historique convertissait 3 démos sur 24 réponses : 7 répondants sur 8
  perdus après la réponse. Le traitement post-réponse pèse autant que
  l'obtention de la réponse.
- 1,2 % de hard bounce : l'enrichissement Apollo était correct (cible moteur :
  < 3 %, vérification avant envoi).
- 0/75 sur `GOOGLE FORM` : sans angle clair, même un petit volume ne produit
  rien.
- Gisement non exploité : les 24 réponses (qui répond — taille de cabinet,
  rôle, étape) n'ont jamais été analysées. À faire avant le premier batch
  d'Azul sur ce marché ; interdiction de recontacter les 418 déjà touchés.

### Note d'infra encore valable

La seule boîte d'envoi existante est `sachalbs@outlook.com` (domaine gratuit) :
plafond de délivrabilité et réputation partagée. Le runbook d'envoi réel du
moteur est `agent/SETUP_OUTLOOK.md` ; domaine secondaire dédié + warmup restent
recommandés avant tout volume.
