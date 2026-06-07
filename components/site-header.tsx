import { Wordmark } from "./wordmark";
import { WideArrow } from "./icons";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-line bg-paper/85 backdrop-blur-md">
      <div className="shell flex h-16 items-center justify-between">
        <a href="#top" aria-label="Azul, accueil">
          <Wordmark />
        </a>

        <nav className="flex items-center">
          <a href="#waitlist" className="btn px-5 py-2.5 text-[0.85rem]">
            Rejoindre la liste
            <WideArrow className="h-2.5 w-6" />
          </a>
        </nav>
      </div>
    </header>
  );
}
