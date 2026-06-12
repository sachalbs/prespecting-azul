# État du moteur (audit du 2026-06-12)

Le "moteur" d'Azul n'est pas du code : c'est **Apollo + une boîte mail +
cette session agent**. Cet audit photographie ce qui existe, les chiffres
réels, et le chemin vers 50 %.

## Architecture actuelle

| Brique | État réel |
|---|---|
| Sourcing | Apollo (+ Lusha, VibeProspecting connectés mais inutilisés) |
| Envoi | 1 seule boîte : `sachalbs@outlook.com`, **domaine gratuit** (Exchange) |
| Séquences | 2 dans Apollo : `comptables` (active), `GOOGLE FORM` (morte) |
| Lecture des réponses | **Impossible pour l'agent** : Gmail MCP non activé, boîte Outlook |
| Mémoire / apprentissage | Aucune avant `azul/` (créé ce jour) ; Notion vide |
| A/B testing | Jamais utilisé (`ab_test_step_ids: []` partout) |

## Les chiffres réels (baseline, pas de la théorie)

Séquence `comptables` (créée 2026-01-18, dernier envoi 2026-04-28, 3 étapes) :

- 423 envoyés, 418 délivrés, 5 hard bounces (1,2 %)
- **24 réponses → 5,7 % de taux de réponse**
- 3 démos (0,7 %)
- Open tracking actif sur seulement 24 envois → opens inexploitables
- Apollo la classe lui-même `is_performing_poorly`, les 3 étapes sous-performantes

Séquence `GOOGLE FORM` : 75 délivrés, 0 réponse, abandonnée sans post-mortem.

**Le vrai point de départ est 5,7 %, pas 0.** L'écart vers 50 % est un ×9.

## Ce qui cloche (par ordre d'impact)

1. **Domaine d'envoi gratuit.** Un outbound depuis `@outlook.com` plafonne la
   délivrabilité et la crédibilité, et on ne contrôle ni SPF/DKIM/DMARC ni la
   réputation. C'est le goulot n°1 : aucun travail de copy ne rattrape un
   message qui n'arrive pas en boîte principale.
2. **Volume générique.** 418 prospects dans une seule séquence templée à
   3 étapes : exactement l'approche "première vague AI SDR" que la marque
   dénonce. Aucun segment, aucun déclencheur daté, aucune personnalisation.
3. **La boucle ne se ferme pas.** L'agent ne peut pas lire les réponses
   (pas d'accès boîte mail). Les 24 réponses de `comptables`, la donnée la
   plus précieuse du compte, n'ont jamais été analysées : qui a répondu,
   à quelle étape, avec quels mots, pourquoi 21 n'ont pas pris de démo.
4. **Zéro expérimentation.** Pas un seul A/B test en 9 mois d'existence du
   compte. Sans variable testée, le taux ne peut pas monter, il dérive.
5. **Moteur à l'arrêt** depuis le 28 avril : la réputation retombe et les
   signaux sourcés périment (un déclencheur > 60 jours est mort).
6. Pas de plafond d'envoi/jour configuré (`max_emails_per_day: null`).

## Chemin vers 50 % (dans l'ordre, pas en parallèle)

**Phase 0 — Infra (préalable à tout envoi)**
- Acheter un domaine secondaire dédié (ex. variante du domaine principal),
  configurer SPF/DKIM/DMARC, 1 à 2 boîtes, warmup 3 semaines.
- Donner à l'agent un accès en lecture à la boîte de réponse (Gmail MCP sur
  une boîte Google Workspace, ou relevé manuel hebdomadaire à défaut) :
  sans lecture des réponses, la boucle de `PLAYBOOK.md` est impossible.

**Phase 1 — Exploiter l'existant (aucun envoi nécessaire)**
- Analyser les 24 réponses de `comptables` dans Apollo : extraire qui répond
  (taille de cabinet, rôle, étape de la séquence) et écrire les premiers
  apprentissages chiffrés dans `SEGMENTS.md` (SEG-04).
- Post-mortem de `GOOGLE FORM` (0/75) : comprendre, archiver.

**Phase 2 — Premier batch nouvelle doctrine**
- Micro-batch ≤ 20 sur SEG-04 (le seul segment avec des données), sourcé sur
  déclencheurs (Apollo job postings, signaux Lusha), 1 variable testée
  (EXP-001 adaptée), tout logué dans `campaigns/log.csv`.
- Objectif du palier : 10 % stable, puis on monte (cf. PLAYBOOK).

**Phase 3 — Industrialiser la boucle**
- Chaque session de prospection suit `CLAUDE.md` : lire le cerveau, envoyer
  petit, mesurer à J+4/J+10, rétro, committer. Le taux par segment dans
  `SEGMENTS.md` est l'unique tableau de bord.
