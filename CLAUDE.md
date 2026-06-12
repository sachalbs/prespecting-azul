# Azul

Ce repo contient deux choses distinctes :

1. **La landing page** (`app/`, `components/`) : site Next.js statique dont le
   seul objectif est l'inscription waitlist. Voir `PRODUCT.md` et `DESIGN.md`.
2. **Le cerveau prospection** (`azul/`) : la mémoire et la doctrine d'Azul en
   tant qu'agent SDR. C'est ce qui lui permet de progresser d'une session à
   l'autre au lieu de repartir de zéro.

## Si la session concerne la prospection

Avant tout sourcing, rédaction ou envoi :

1. Lire `azul/PLAYBOOK.md` (la doctrine : boucle, règles, seuils).
2. Lire `azul/SEGMENTS.md` (ce qui marche par type de client, avec les chiffres).
3. Lire `azul/EXPERIMENTS.md` (l'hypothèse en cours de test : un batch = une
   variable testée).

Après chaque batch envoyé et après chaque relevé de réponses :

- Loguer chaque message dans `azul/campaigns/log.csv` (une ligne par prospect).
- Mettre à jour les compteurs et apprentissages du segment dans
  `azul/SEGMENTS.md`.
- Clore ou prolonger l'expérience dans `azul/EXPERIMENTS.md`.
- Committer ces fichiers : la mémoire d'Azul n'existe que si elle est poussée.

**Règle absolue : aucun envoi sans log, aucun log sans relevé d'issue.** Un
message dont on ne mesure pas le résultat n'apprend rien à personne.

## Si la session concerne le site

`npm run dev` / `npm run build`. Page unique, statique, bilingue EN/FR (EN
canonique) via `components/lang-provider.tsx`. Respecter `PRODUCT.md` :
honnêteté totale, pas de fausse social proof, le taux de réponse est le héros.
