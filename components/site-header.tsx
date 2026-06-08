"use client";

import { Wordmark } from "./wordmark";
import { WideArrow } from "./icons";
import { WaitlistTrigger } from "./waitlist-trigger";
import { useLang } from "./lang-provider";

export function SiteHeader() {
  const { lang, setLang, t } = useLang();
  return (
    <header className="sticky top-0 z-50 border-b border-line bg-paper/85 backdrop-blur-md">
      <div className="shell flex h-16 items-center justify-between">
        <a href="#top" aria-label="Azul">
          <Wordmark />
        </a>

        <nav className="flex items-center gap-2.5 sm:gap-3">
          {/* language toggle: English is the principal version */}
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

          <WaitlistTrigger className="btn whitespace-nowrap px-3.5 py-2 text-[0.72rem] sm:px-5 sm:py-2.5 sm:text-[0.85rem]">
            {t.cta}
            <WideArrow className="h-2.5 w-5 sm:w-6" />
          </WaitlistTrigger>
        </nav>
      </div>
    </header>
  );
}
