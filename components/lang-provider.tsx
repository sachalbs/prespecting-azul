"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

export type Lang = "en" | "fr";

const dict = {
  en: {
    cta: "Join the waitlist",
    hero: {
      sysPost: "// autonomous prospecting engine",
      sysActive: "system active",
      h1a: "The right message,",
      h1b: "to the right prospect.",
      sub: "An engine that studies every prospect and writes the message that earns a reply.",
      why: "Why Azul",
      pilotedFrom: "Driven from",
      prospectsVia: "Prospects via",
      blobAria: "Join the waitlist",
    },
    problem: {
      tag: "The problem",
      hPre: "Your prospects are buried in generic",
      hAccent: "messages.",
      sub: "The first wave of “AI SDRs” optimized for volume. Azul flips the problem.",
      volumeTitle: "The volume approach",
      oldWay: [
        "Barely personalized templates",
        "Always more sends",
        "Burned prospects, damaged reputation",
        "You measure volume",
      ],
      punch: "→ Result: you land in spam.",
      azulTag: "Azul’s approach: a message written for Camille",
    },
    card: {
      role: "Head of Sales · Lumen",
      signals: "4 signals",
      chips: [
        "Series A · 3 weeks ago",
        "Hiring 4 SDRs",
        "HubSpot + Apollo",
        "Posted about outbound",
      ],
      greeting: "Hi Camille,",
      bodyLines: [
        [
          "Your ",
          "Series A announced last month",
          " and the ",
          "4 open SDR roles",
          " point to the same priority: build outbound fast, without saturating it.",
        ],
        [
          "You’re already on ",
          "HubSpot and Apollo",
          ". I have a precise approach in mind for your first sequences. Ten minutes next week?",
        ],
      ],
      draft: "Draft · to approve",
    },
    how: {
      tag: "The process",
      hPre: "From research to reply, in ",
      hAccent: "three steps.",
      steps: [
        {
          title: "Research",
          desc: "Funding, hiring, stack, intent signals. Real context, not a {{firstName}} variable.",
        },
        {
          title: "Writing",
          desc: "A personal, referenced message, tuned to your offer and your tone.",
        },
        {
          title: "Send & learn",
          desc: "You approve the first ones, it calibrates the rest, sends, and improves campaign after campaign.",
        },
      ],
    },
    waitlist: {
      tag: "Early access",
      h: "Join the waitlist.",
      sub: "Azul is in early access. No public customers, no numbers to flaunt. We’re building it with the first teams.",
      note: "We onboard in small waves, in signup order.",
    },
    form: {
      label: "Work email",
      placeholder: "you@company.com",
      submit: "Join the waitlist",
      loading: "One moment…",
      successTitle: "You’re on the list.",
      successBody: "We’ll email you as soon as a wave of access opens.",
      errEmail: "Enter a valid email address.",
      errGeneric: "Something went wrong. Try again in a moment.",
    },
    footer: {
      tagline: "The autonomous rep that gets your prospects to reply.",
      problem: "The problem",
      waitlist: "Waitlist",
      rights: "Early access",
    },
  },
  fr: {
    cta: "Rejoindre la liste",
    hero: {
      sysPost: "// moteur de prospection autonome",
      sysActive: "système actif",
      h1a: "Le bon message,",
      h1b: "au bon prospect.",
      sub: "Un moteur qui étudie chaque prospect et écrit le message qui fait répondre.",
      why: "Pourquoi Azul",
      pilotedFrom: "Piloté depuis",
      prospectsVia: "Prospecte via",
      blobAria: "Rejoindre la liste d’attente",
    },
    problem: {
      tag: "Le problème",
      hPre: "Vos prospects sont saturés de messages",
      hAccent: "génériques.",
      sub: "La première vague de « SDR IA » a optimisé le volume. Azul prend le problème à l’envers.",
      volumeTitle: "L’approche au volume",
      oldWay: [
        "Templates à peine personnalisés",
        "Toujours plus d’envois",
        "Prospects grillés, réputation abîmée",
        "On mesure le volume",
      ],
      punch: "→ Résultat : vous finissez en spam.",
      azulTag: "L’approche d’Azul : un message écrit pour Camille",
    },
    card: {
      role: "Head of Sales · Lumen",
      signals: "4 signaux",
      chips: [
        "Série A · il y a 3 semaines",
        "Recrute 4 SDR",
        "HubSpot + Apollo",
        "A publié sur l’outbound",
      ],
      greeting: "Bonjour Camille,",
      bodyLines: [
        [
          "Votre ",
          "Série A annoncée le mois dernier",
          " et les ",
          "4 postes de SDR ouverts",
          " pointent vers la même priorité : structurer l’outbound vite, sans le saturer.",
        ],
        [
          "Vous êtes déjà sur ",
          "HubSpot et Apollo",
          ". J’ai une approche précise en tête pour vos premières séquences. Dix minutes la semaine prochaine ?",
        ],
      ],
      draft: "Brouillon · à valider",
    },
    how: {
      tag: "Le process",
      hPre: "De la recherche à la réponse, en ",
      hAccent: "trois temps.",
      steps: [
        {
          title: "Recherche",
          desc: "Levées, recrutements, stack, signaux d’intérêt. Du contexte réel, pas une variable {{prénom}}.",
        },
        {
          title: "Rédaction",
          desc: "Un message personnel et référencé, calé sur votre offre et votre ton.",
        },
        {
          title: "Envoi & apprentissage",
          desc: "Vous validez les premiers, il calibre le reste, envoie et s’améliore campagne après campagne.",
        },
      ],
    },
    waitlist: {
      tag: "Accès anticipé",
      h: "Rejoignez la liste d’attente.",
      sub: "Accès anticipé. Pas de clients publics ni de chiffres à brandir : on construit avec les premières équipes.",
      note: "On onboarde par petites vagues, dans l’ordre d’inscription.",
    },
    form: {
      label: "Email professionnel",
      placeholder: "vous@entreprise.com",
      submit: "Rejoindre la liste",
      loading: "Un instant…",
      successTitle: "Vous êtes sur la liste.",
      successBody: "Nous vous écrivons dès qu’une vague d’accès s’ouvre.",
      errEmail: "Indiquez une adresse email valide.",
      errGeneric: "Un souci est survenu. Réessayez dans un instant.",
    },
    footer: {
      tagline: "Le commercial autonome qui fait répondre vos prospects.",
      problem: "Le problème",
      waitlist: "Liste d’attente",
      rights: "Accès anticipé",
    },
  },
} as const;

export type Dict = (typeof dict)["en"];

const LangContext = createContext<{
  lang: Lang;
  setLang: (l: Lang) => void;
  t: Dict;
}>({ lang: "en", setLang: () => {}, t: dict.en });

export function LangProvider({ children }: { children: ReactNode }) {
  // English is the principal version: it's the deterministic default for SSR
  // and the first client render (avoids hydration mismatch).
  const [lang, setLangState] = useState<Lang>("en");

  useEffect(() => {
    const saved = localStorage.getItem("azul-lang");
    if (saved === "fr" || saved === "en") setLangState(saved);
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = (l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem("azul-lang", l);
    } catch {
      /* ignore */
    }
  };

  return (
    <LangContext.Provider value={{ lang, setLang, t: dict[lang] as Dict }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLang() {
  return useContext(LangContext);
}
