# État des lieux prospection (audit du 2026-06-12, corrigé)

**Source des données : le compte Apollo personnel de Sacha**, lu via le
connecteur MCP Apollo (`apollo_emailer_campaigns_search`,
`apollo_email_accounts_index`). Ces chiffres décrivent la prospection
**manuelle, historique, pré-Azul**. Ils ne sont PAS le bilan d'Azul.

## Deux choses à ne jamais confondre

### 1. La campagne Apollo historique (humaine, pré-Azul)

Prospection menée à la main depuis le compte Apollo, boîte d'envoi
`sachalbs@outlook.com` (domaine gratuit, Exchange) :

- Séquence `comptables` (2026-01-18 → 2026-04-28, 3 étapes, générique,
  sans segment ni déclencheur) : 423 envoyés, 418 délivrés, 5 hard bounces
  (1,2 %), **24 réponses (5,7 %)**, 3 démos (0,7 %). Apollo la classe
  `is_performing_poorly`, les 3 étapes sous-performantes. Aucun A/B test.
- Séquence `GOOGLE FORM` (sept. 2025) : 75 délivrés, 0 réponse, abandonnée.

Statut : c'est un **benchmark**, pas une performance d'Azul. Sa valeur :
(a) il fixe la barre à battre sur le marché des experts-comptables — un
templé générique y fait 5,7 % ; (b) ses 24 réponses sont une mine
d'information jamais analysée sur qui répond et pourquoi.

### 2. Azul (l'agent)

- **Envois : 0. Réponses : 0. Taux : aucun — il n'existe pas encore.**
- Azul n'est aujourd'hui que : sa doctrine (`azul/PLAYBOOK.md`,
  `SEGMENTS.md`, `EXPERIMENTS.md`, `campaigns/log.csv`, tous vierges de
  données d'envoi) + les connecteurs disponibles (Apollo, Lusha,
  VibeProspecting, Calendar ; pas d'accès en lecture à une boîte mail).
- Son premier batch sera son premier point de données. Tout chiffre
  attribué à Azul doit provenir de `campaigns/log.csv`, de rien d'autre.

## Ce que le benchmark humain apprend à Azul (sans se l'approprier)

- Le marché expert-comptable répond à ~5,7 % à du templé 3 étapes sans
  personnalisation : c'est le plancher. Si Azul, avec recherche prospect
  et micro-batches, ne bat pas nettement ce chiffre, sa thèse est fausse.
- Le CTA historique convertissait 3 démos sur 24 réponses : 7 répondants
  sur 8 perdus après la réponse. Le traitement de la réponse compte autant
  que l'obtenir.
- 1,2 % de hard bounce : la qualité d'enrichissement Apollo était correcte.
- 0/75 sur `GOOGLE FORM` : un envoi sans angle clair ne produit rien,
  même petit volume.

## Contraintes d'infra (communes aux deux, à lever avant le 1er envoi d'Azul)

1. **La seule boîte d'envoi connectée est `sachalbs@outlook.com`, domaine
   gratuit.** Si Azul envoie depuis cette boîte, il hérite du plafond de
   délivrabilité et de la réputation existante. Prérequis : domaine
   secondaire dédié + SPF/DKIM/DMARC + warmup ~3 semaines.
2. **Azul ne peut pas lire les réponses** (Gmail MCP non activé, boîte
   Outlook). Sans lecture des réponses, la boucle mesure→rétro du playbook
   est inapplicable : accès mail en lecture, ou relevé manuel hebdomadaire.

## Plan de lancement d'Azul (dans l'ordre)

- **Phase 0 — Infra** : domaine + boîtes + warmup ; accès lecture réponses.
- **Phase 1 — Apprendre du benchmark (0 envoi)** : analyser les 24 réponses
  de la campagne historique dans Apollo (qui répond : taille de cabinet,
  rôle, étape) → premiers apprentissages chiffrés dans `SEGMENTS.md`
  (SEG-04), clairement étiquetés "benchmark humain".
- **Phase 2 — Premier batch Azul** : ≤ 20 prospects sur SEG-04, sourcés sur
  déclencheurs datés, 1 variable testée, exclusion stricte des 418 déjà
  contactés, tout logué dans `campaigns/log.csv`. C'est la ligne 1 de
  l'historique d'Azul.
- **Phase 3 — La boucle** : mesure J+4/J+10, rétro chiffrée, commit, batch
  suivant. Objectif palier 1 : battre le benchmark (> 5,7 %), viser 10 %
  stable, puis 20, 35, 50.
