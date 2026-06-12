"use client";

import Link from "next/link";
import { Wordmark } from "./wordmark";
import { useLang } from "./lang-provider";

/** Slim header for onboarding: same chrome as the landing, no CTA — the page
    itself is the one decision. */
export function ConnectHeader() {
  const { lang, setLang, t } = useLang();
  return (
    <header className="sticky top-0 z-50 border-b border-line bg-paper/85 backdrop-blur-md">
      <div className="shell flex h-16 items-center justify-between">
        <Link href="/" aria-label={t.connect.back}>
          <Wordmark />
        </Link>

        <div className="flex items-center border border-ink font-mono text-[0.7rem] font-semibold uppercase">
          <button
            type="button"
            onClick={() => setLang("en")}
            aria-pressed={lang === "en"}
            className={`px-2.5 py-1.5 transition-colors ${
              lang === "en" ? "bg-ink text-paper" : "text-ink hover:bg-ink/5"
            }`}
          >
            EN
          </button>
          <button
            type="button"
            onClick={() => setLang("fr")}
            aria-pressed={lang === "fr"}
            className={`px-2.5 py-1.5 transition-colors ${
              lang === "fr" ? "bg-ink text-paper" : "text-ink hover:bg-ink/5"
            }`}
          >
            FR
          </button>
        </div>
      </div>
    </header>
  );
}
