import { Wordmark } from "./wordmark";

export function SiteFooter() {
  return (
    <footer className="border-t border-ink">
      <div className="shell flex flex-col gap-8 py-12 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <Wordmark />
          <p className="mt-3 max-w-xs text-[0.9rem] leading-relaxed text-muted">
            Le commercial autonome qui fait répondre vos prospects.
          </p>
        </div>

        <div className="flex flex-col gap-4 sm:items-end">
          <nav className="flex flex-wrap gap-x-6 gap-y-2">
            <a href="#problem" className="text-[0.72rem] font-semibold uppercase tracking-label text-muted transition-colors hover:text-ink">
              Le problème
            </a>
            <a href="#waitlist" className="text-[0.72rem] font-semibold uppercase tracking-label text-muted transition-colors hover:text-ink">
              Liste d’attente
            </a>
          </nav>
          <p className="text-[0.72rem] font-semibold uppercase tracking-label text-muted/80">
            © {new Date().getFullYear()} Azul — Accès anticipé
          </p>
        </div>
      </div>
    </footer>
  );
}
