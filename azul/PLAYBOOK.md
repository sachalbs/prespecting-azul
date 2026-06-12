# Playbook prospection Azul

> **Le moteur est `agent/`. La source de vérité des envois est la table
> `outcomes`. Ce dossier = benchmarks humains et notes opérateur.**

Objectif unique : le **taux de réponse qualifiée**. Pas le volume. La cible
long terme est 50 % de réponses ; on y tend par paliers mesurés, jamais par
affirmation.

## La réalité des chiffres (pour rester honnête)

- Cold email moyen du marché : 1 à 5 % de réponses.
- Personnalisation sérieuse, signaux réels : 10 à 20 %.
- 30 %+ : micro-batches (≤ 20), déclencheur chaud daté, multicanal, relances.
- 50 % : atteignable uniquement sur de très petits lots ultra-ciblés où chaque
  prospect a un événement déclencheur de moins de 30 jours et où le message
  serait impossible à envoyer à quelqu'un d'autre.

Le palier en cours est noté en tête de `SEGMENTS.md`. On ne vise pas 50 %
demain ; on vise +5 points par cycle, segment par segment.

## La boucle (chaque campagne la parcourt en entier)

```
1 SOURCER → 2 SEGMENTER → 3 RECHERCHER → 4 RÉDIGER → 5 ENVOYER → 6 MESURER → 7 RÉTRO
                ↑                                                              |
                └──────────────── les apprentissages reviennent ───────────────┘
```

### 1. Sourcer

Apollo / Lusha / VibeProspecting. On ne source jamais "une liste" : on source
des **événements** (levée, recrutements ouverts, changement de poste, post
LinkedIn, signal d'intention). Un prospect sans déclencheur daté de moins de
60 jours ne rentre pas dans le batch.

### 2. Segmenter

Chaque prospect est rattaché à un segment de `SEGMENTS.md` (rôle × stade ×
contexte). Si aucun segment ne colle, on en crée un avec le template, plutôt
que de forcer un prospect dans un angle qui n'est pas le sien. **C'est ici que
se joue l'adaptation au type de client** : l'angle, le ton et le CTA viennent
du segment, jamais d'un template global.

### 3. Rechercher

Minimum **2 signaux datés et vérifiables** par prospect (levée, postes ouverts,
stack, contenu publié). Un signal invérifiable ne se cite pas. La recherche
sert le prospect, pas la flatterie : chaque signal cité doit pointer vers le
problème qu'on résout.

### 4. Rédiger

- Le brouillon suit la fiche du segment : angle, ton, CTA, longueur.
- Test du "message impossible à transférer" : si le message pouvait être envoyé
  tel quel à un autre prospect, il est refusé.
- Un batch teste **une seule variable** (objet, angle, CTA, longueur, canal,
  heure d'envoi), déclarée dans `EXPERIMENTS.md` AVANT l'envoi. Moitié du batch
  en contrôle, moitié en variante.

### 5. Envoyer

- Batch ≤ 20 prospects. Petit lot = signal propre = apprentissage rapide,
  et le domaine reste sain.
- Premiers messages validés par l'humain tant que le segment a moins de
  30 envois d'historique.
- Chaque envoi est logué immédiatement dans `campaigns/log.csv`.
- Relance des silencieux à J+4 (angle différent, jamais un "did you see my
  email"), seconde relance J+10, puis stop.

### 6. Mesurer

À J+4 et J+10, relever les réponses (recherche Gmail sur le thread de chaque
prospect logué) et remplir `outcome` dans le log :

- `reply_positive` : réponse engageante (question, intérêt, RDV)
- `reply_neutral` : réponse polie sans suite ("pas maintenant")
- `reply_negative` : refus / désinscription
- `no_reply` : silence après les deux relances
- `bounce` : adresse invalide (à exclure du dénominateur)

Taux de réponse = (positives + neutres + négatives) / (envoyés − bounces).
Le taux **qualifié** = positives / (envoyés − bounces). Les deux se trackent.

### 7. Rétro (le cœur de l'apprentissage)

Après chaque relevé J+10, obligatoirement :

1. Calculer le taux du batch, par segment et par variante.
2. Mettre à jour les compteurs cumulés du segment dans `SEGMENTS.md`.
3. Écrire 1 à 3 apprentissages **falsifiables** dans la fiche segment
   ("citer le montant de la levée fait moins bien que citer les postes
   ouverts : 12 % vs 26 % sur n=17"), pas des impressions.
4. Trancher l'expérience dans `EXPERIMENTS.md` (gagnante → promue dans la
   fiche segment ; perdante → archivée avec le chiffre).
5. Committer. Une rétro non commitée n'a pas eu lieu.

## Seuils de décision (pas de débat, on applique)

| Situation | Décision |
|---|---|
| Segment < 10 % de réponses sur n ≥ 30 | Angle mort : on réécrit la fiche segment de zéro |
| Segment entre 10 et 20 % sur n ≥ 30 | On continue, une expérience active en permanence |
| Variante bat le contrôle avec n ≥ 20 par bras | Promue comme nouveau contrôle du segment |
| Deux batches consécutifs en baisse sur un segment | Stop envois, diagnostic (saturation ? signal périmé ?) |
| Taux de bounce > 5 % sur un batch | Revoir la source d'enrichissement avant tout nouvel envoi |
| Prospect sans déclencheur < 60 jours | Hors batch, sans exception |

## Le log (`campaigns/log.csv`)

Une ligne par prospect contacté. Colonnes notables : `batch_id`
(AAAA-MM-JJ-segment, ex. `2026-06-15-SEG-01`), `experiment`/`arm` (EXP-XXX et
`control`/`variant`, vides hors test), `trigger_signal`/`trigger_date` (le
déclencheur qui a justifié l'envoi), `subject_or_hook` (objet email ou première
ligne LinkedIn), `outcome` (cf. § Mesurer), `meeting_booked` (oui/non). Le CSV
est la source de vérité ; les stats de `SEGMENTS.md` doivent toujours pouvoir
être recalculées depuis lui.

## Anti-patterns (ce qui a tué la première vague des "AI SDR")

- Augmenter le volume pour compenser un taux qui baisse.
- Tester trois variables à la fois (= n'apprendre rien).
- Citer un signal pour montrer qu'on a cherché, sans le relier au problème.
- Garder en mémoire ("on sait que…") un apprentissage qui n'est écrit nulle
  part avec son chiffre.
