"use client";

import { Wordmark } from "./wordmark";
import { WideArrow } from "./icons";
import { WaitlistTrigger } from "./waitlist-trigger";
import { useLang } from "./lang-provider";

function FooterLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <a
      href={href}
      className="text-[0.74rem] font-semibold uppercase tracking-label text-muted transition-colors hover:text-ink"
    >
      {children}
    </a>
  );
}

export function SiteFooter() {
  const { t } = useLang();
  return (
    <footer className="border-t border-ink bg-paper">
      <div className="shell">
        {/* brand + navigation + CTA */}
        <div className="grid gap-10 py-14 md:grid-cols-[1.3fr_1fr] md:gap-16">
          <div>
            <Wordmark />
            <p className="mt-4 max-w-sm text-[0.98rem] leading-relaxed text-muted">
              {t.footer.tagline}
            </p>
            <span className="mt-6 inline-flex items-center gap-2.5 font-mono text-[0.7rem] uppercase tracking-label text-ink">
              <span className="relative flex h-2 w-2" aria-hidden>
                <span className="absolute inline-flex h-full w-full animate-ping bg-cobalt opacity-70" />
                <span className="relative inline-flex h-2 w-2 bg-cobalt" />
              </span>
              {t.footer.status}
            </span>
          </div>

          <div className="flex flex-col gap-6 md:items-end">
            <nav className="flex flex-wrap gap-x-6 gap-y-3 md:justify-end">
              <FooterLink href="#problem">{t.footer.problem}</FooterLink>
              <FooterLink href="#how">{t.how.tag}</FooterLink>
              <FooterLink href="#manage">{t.manage.tag}</FooterLink>
              <FooterLink href="#faq">{t.faq.tag}</FooterLink>
            </nav>
            <WaitlistTrigger className="btn px-5 py-2.5 text-[0.78rem]">
              {t.cta}
              <WideArrow className="h-2.5 w-5" />
            </WaitlistTrigger>
          </div>
        </div>

        {/* small print */}
        <div className="flex flex-col gap-3 border-t border-line py-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="font-mono text-[0.68rem] uppercase tracking-label text-muted">
            © {new Date().getFullYear()} Azul · {t.footer.rights}
          </p>
          <p className="font-mono text-[0.68rem] uppercase tracking-label text-muted/70">
            {t.footer.channels}
          </p>
        </div>
      </div>
    </footer>
  );
}
