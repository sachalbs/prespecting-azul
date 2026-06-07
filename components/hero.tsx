import type { CSSProperties, ReactNode } from "react";
import {
  ArrowRight,
  SlackMark,
  WhatsAppMark,
  TeamsMark,
  MailMark,
  LinkedInMark,
} from "./icons";

function d(ms: number): CSSProperties {
  return { "--d": `${ms}ms` } as CSSProperties;
}

function ChannelLogo({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-[0.9rem] font-medium text-ink/80">
      <span className="text-ink">{icon}</span>
      {label}
    </span>
  );
}

function MessageBubble() {
  return (
    <figure className="ml-auto w-full max-w-sm">
      <div className="rounded-[1.6rem] rounded-br-md bg-cobalt px-6 py-5 text-white shadow-[0_20px_44px_-18px_rgba(44,78,230,0.6)]">
        <p className="font-mono text-[0.64rem] uppercase tracking-[0.16em] text-white/65">
          Azul · écrit pour Camille Roche
        </p>
        <p className="mt-3 text-[0.92rem] leading-relaxed text-white/95">
          Bonjour Camille — votre{" "}
          <span className="font-semibold">Série A</span> et vos{" "}
          <span className="font-semibold">4 recrutements SDR</span> pointent
          vers la même priorité. J’ai une approche précise pour vos premières
          séquences. Dix minutes la semaine prochaine&nbsp;?
        </p>
      </div>
      <figcaption className="mt-2 text-right font-mono text-[0.62rem] uppercase tracking-[0.16em] text-muted">
        message généré · à valider
      </figcaption>
    </figure>
  );
}

export function Hero() {
  return (
    <section id="top" className="relative overflow-hidden border-b border-line">
      <div aria-hidden className="grid-paper pointer-events-none absolute inset-0" />

      <div className="shell relative pb-14 pt-6 lg:pb-20">
        {/* system bar */}
        <div
          className="enter flex items-center justify-between border-b border-line py-3 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-muted"
          style={d(0)}
        >
          <span>
            <span className="text-ink">azul</span> // moteur de prospection
            autonome
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            système actif
          </span>
        </div>

        {/* headline (smaller) + blue bubble */}
        <div className="grid items-center gap-10 pt-12 lg:grid-cols-[1.05fr_minmax(300px,380px)] lg:gap-14 lg:pt-16">
          <div>
            <h1 className="text-[clamp(2.3rem,5.4vw,4.4rem)]">
              <span className="rise-wrap">
                <span className="rise display text-ink" style={d(120)}>
                  Le bon message,
                </span>
              </span>
              <span className="rise-wrap">
                <span className="rise display text-cobalt" style={d(240)}>
                  au bon prospect.
                </span>
              </span>
            </h1>

            <p
              className="enter mt-6 max-w-md text-[1.08rem] leading-relaxed text-muted"
              style={d(420)}
            >
              Un moteur qui étudie chaque prospect et écrit le message qui fait
              répondre.
            </p>

            <div
              className="enter mt-7 flex flex-wrap items-center gap-x-6 gap-y-3"
              style={d(520)}
            >
              <a href="#waitlist" className="btn">
                Rejoindre la liste
                <ArrowRight className="h-4 w-4" />
              </a>
              <a
                href="#problem"
                className="font-mono text-[0.74rem] font-medium uppercase tracking-[0.14em] text-muted transition-colors hover:text-ink"
              >
                ▸ pourquoi azul
              </a>
            </div>
          </div>

          <div className="enter" style={d(440)}>
            <MessageBubble />
          </div>
        </div>

        {/* channel logos */}
        <div className="enter mt-12 flex flex-col gap-3 border-t border-line pt-6 sm:flex-row sm:items-center sm:justify-between" style={d(620)}>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
            <span className="font-mono text-[0.7rem] uppercase tracking-[0.14em] text-muted">
              Piloté depuis
            </span>
            <ChannelLogo icon={<SlackMark className="h-[1.15rem] w-[1.15rem]" />} label="Slack" />
            <ChannelLogo icon={<WhatsAppMark className="h-[1.15rem] w-[1.15rem]" />} label="WhatsApp" />
            <ChannelLogo icon={<TeamsMark className="h-[1.15rem] w-[1.15rem]" />} label="Teams" />
          </div>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
            <span className="font-mono text-[0.7rem] uppercase tracking-[0.14em] text-muted">
              Prospecte via
            </span>
            <ChannelLogo icon={<MailMark className="h-[1.15rem] w-[1.15rem]" />} label="Email" />
            <ChannelLogo icon={<LinkedInMark className="h-[1.15rem] w-[1.15rem]" />} label="LinkedIn" />
          </div>
        </div>
      </div>
    </section>
  );
}
