import { WaitlistForm } from "./waitlist-form";
import { Reveal } from "./reveal";

export function Hero() {
  return (
    <section id="top" className="relative">
      <div className="shell pb-12 pt-14 sm:pt-20 lg:pb-16">
        {/* top meta */}
        <Reveal>
          <div className="flex items-center justify-between gap-4">
            <span className="label">
              <span className="sq" />
              Commercial autonome · SDR IA
            </span>
            <span className="hidden text-[0.72rem] font-semibold uppercase tracking-label text-muted/70 sm:block">
              Accès anticipé
            </span>
          </div>
        </Reveal>

        {/* headline */}
        <Reveal delay={60}>
          <h1 className="display mt-7 text-[clamp(2.9rem,9vw,7.5rem)] text-ink">
            Le bon message,
            <br />
            <span className="text-cobalt">au bon prospect.</span>
          </h1>
        </Reveal>

        <div className="mt-10 border-t border-line" />

        {/* copy + form */}
        <div className="grid items-start gap-10 pt-10 lg:grid-cols-[1.05fr_0.95fr] lg:gap-16">
          <Reveal delay={100}>
            <p className="max-w-md text-[1.15rem] leading-relaxed text-muted">
              Azul recherche chaque prospect et lui écrit un message{" "}
              <strong className="font-semibold text-ink">
                vraiment personnel
              </strong>
              . Résultat : beaucoup plus de{" "}
              <strong className="font-semibold text-ink">réponses</strong>.
            </p>
          </Reveal>

          <Reveal delay={150}>
            <div>
              <WaitlistForm />
              <p className="text-[0.83rem] text-muted">
                Accès anticipé, par petites vagues. Pas de carte bancaire.
                Désinscription en un clic.
              </p>
            </div>
          </Reveal>
        </div>

        {/* bottom meta strip */}
        <Reveal delay={120}>
          <div className="mt-12 flex flex-col gap-3 border-t border-line pt-6 sm:flex-row sm:items-center sm:justify-between">
            <span className="text-[0.72rem] font-semibold uppercase tracking-label text-muted">
              <span className="text-ink">Piloté depuis</span>{" "}
              — Slack · WhatsApp · Teams
            </span>
            <span className="text-[0.72rem] font-semibold uppercase tracking-label text-muted">
              <span className="text-ink">Prospecte via</span> — Email · LinkedIn
            </span>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
