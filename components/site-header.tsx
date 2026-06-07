import { Wordmark } from "./wordmark";
import { ArrowRight } from "./icons";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-line bg-paper/85 backdrop-blur-md">
      <div className="shell flex h-16 items-center justify-between">
        <a href="#top" aria-label="Azul, accueil">
          <Wordmark />
        </a>

        <nav className="flex items-center gap-6">
          <a
            href="#how"
            className="hidden text-[0.72rem] font-semibold uppercase tracking-label text-muted transition-colors hover:text-ink md:inline-block"
          >
            Comment ça marche
          </a>
          <a
            href="#pilot"
            className="hidden text-[0.72rem] font-semibold uppercase tracking-label text-muted transition-colors hover:text-ink md:inline-block"
          >
            Le pilotage
          </a>
          <a
            href="#waitlist"
            className="btn px-5 py-2.5 text-[0.85rem]"
          >
            Rejoindre la liste
            <ArrowRight className="h-3.5 w-3.5" />
          </a>
        </nav>
      </div>
    </header>
  );
}
