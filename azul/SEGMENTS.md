# Segments

Palier en cours : **palier 1 — objectif 10 % de réponses stables** (puis 20 %,
35 %, 50 %). **Azul : 0 envoi à ce jour.** Benchmark à battre : 5,7 %, score
de la campagne Apollo manuelle pré-Azul (cf. `ENGINE.md` — ce chiffre n'est
pas une performance d'Azul). Les compteurs `Stats` ci-dessous ne comptent que
les envois d'Azul, recalculables depuis `campaigns/log.csv` ; ils se mettent à
jour à chaque rétro, jamais de tête.

---

## Template (copier pour tout nouveau segment)

```
## SEG-XX · Nom du segment

Profil      : rôle × stade × contexte (ex. Head of Sales · SaaS Série A · équipe < 5 SDR)
Déclencheurs: les événements qui font entrer un prospect ici (datés < 60 j)
Douleur     : le problème vécu, dans leurs mots
Angle       : la connexion signal → douleur → notre offre
Ton         : registre, longueur, vouvoiement/tutoiement
CTA         : la demande exacte qui convertit le mieux (actuellement)
Ne pas faire: les erreurs déjà mesurées sur ce segment

Stats       : envoyés=0 · réponses=0 · positives=0 · taux=— · taux qualifié=—
Apprentissages (datés, chiffrés) :
- (vide)
```

---

## SEG-01 · Head of Sales · SaaS Série A

Profil      : Head of Sales / VP Sales, SaaS B2B post-Série A (< 18 mois),
              équipe outbound en construction (0–5 SDR).
Déclencheurs: levée annoncée ; postes SDR/AE ouverts ; arrivée récente au poste.
Douleur     : pression du board sur le pipeline, obligé de monter l'outbound
              vite sans cramer le domaine ni recruter trop tôt.
Angle       : leurs signaux publics (levée + recrutements) pointent la même
              priorité ; on aide à la tenir sans saturer le marché.
Ton         : vouvoiement, direct, 60–90 mots, zéro flatterie, un seul lien max.
CTA         : créneau court et daté ("dix minutes la semaine prochaine ?"),
              jamais "un call pour échanger".
Ne pas faire: ouvrir sur des félicitations pour la levée (tout le monde le fait).

Stats       : envoyés=0 · réponses=0 · positives=0 · taux=— · taux qualifié=—
Apprentissages (datés, chiffrés) :
- (vide — premier batch à venir)

---

## SEG-02 · Founder · early-stage (pré-seed/seed)

Profil      : founder/CEO qui fait son outbound lui-même, < 15 personnes.
Déclencheurs: lancement produit, post LinkedIn sur la prospection/les ventes,
              première embauche sales.
Douleur     : le temps. L'outbound marche un peu mais lui coûte ses soirées ;
              embaucher un SDR est prématuré.
Angle       : pair-à-pair ; on parle du coût en temps, pas de "scaler".
Ton         : plus court (40–70 mots), moins formel, une seule idée.
CTA         : réponse à faible friction ("c'est un sujet chez vous en ce
              moment ?") plutôt qu'un RDV direct.
Ne pas faire: vocabulaire corporate ("optimiser votre pipeline") ; pitcher la
              feature au lieu du temps gagné.

Stats       : envoyés=0 · réponses=0 · positives=0 · taux=— · taux qualifié=—
Apprentissages (datés, chiffrés) :
- (vide)

---

## SEG-03 · RevOps / Sales Ops · scale-up (Série B+)

Profil      : RevOps, Sales Ops, parfois Head of Growth ; équipe SDR existante,
              stack outbound déjà en place (Outreach/Salesloft/Apollo).
Déclencheurs: offre d'emploi RevOps/SDR mentionnant la stack ; migration
              d'outil ; baisse publique de délivrabilité (posts, forums).
Douleur     : les taux de réponse s'effondrent malgré la stack ; la qualité des
              messages ne suit pas le volume que la stack permet.
Angle       : data-first ; on parle taux de réponse et délivrabilité, chiffres
              à l'appui, pas de storytelling.
Ton         : technique, précis, 70–100 mots ; citer leur stack exacte.
CTA         : proposer un échantillon concret ("je vous montre 3 messages
              écrits pour vos ICP ?") plutôt qu'une démo.
Ne pas faire: critiquer leur stack (ils l'ont choisie) ; promettre un % précis.

Stats       : envoyés=0 · réponses=0 · positives=0 · taux=— · taux qualifié=—
Apprentissages (datés, chiffrés) :
- (vide)

---

## SEG-04 · Experts-comptables

Segment hérité du marché déjà travaillé manuellement (campagne Apollo
`comptables`, pré-Azul). Les chiffres de cette campagne sont un **benchmark
humain**, pas des stats d'Azul : ils ne rentrent jamais dans la ligne `Stats`.

Profil      : cabinets d'expertise comptable.
Déclencheurs: à définir — la campagne manuelle n'en utilisait aucun
              (candidats : offres d'emploi collaborateur, période fiscale,
              changement d'outil, croissance du cabinet).
Douleur     : à valider via l'analyse des 24 réponses du benchmark.
Angle       : à définir — le copy des 3 étapes manuelles vit dans Apollo,
              à auditer comme matière première, pas comme modèle.
Ton         : à définir après analyse des réponses.
CTA         : à définir.
Ne pas faire: recontacter les 418 prospects de la campagne manuelle ;
              séquence unique sans segment.

Benchmark humain (Apollo `comptables`, 2026-01→04, ne pas cumuler ici) :
              418 délivrés · 24 réponses (5,7 %) · 3 démos · 1,2 % hard bounce ·
              CTA : 3 démos / 24 réponses = 7 répondants sur 8 perdus.

Stats       : envoyés=0 · réponses=0 · positives=0 · taux=— · taux qualifié=—
Apprentissages (datés, chiffrés) :
- 2026-06-12 : benchmark établi (cf. ci-dessus et `ENGINE.md`). Azul devra
  battre 5,7 % dès son premier batch pour valider sa thèse. Première action
  avant tout envoi : lire les 24 réponses du benchmark et qualifier qui répond.
