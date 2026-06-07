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

export function Hero() {
  return (
    <section id="top" className="relative overflow-hidden border-b border-line">
      <div aria-hidden className="grid-paper pointer-events-none absolute inset-0" />

      <div className="shell relative pb-16 pt-6 lg:pb-24">
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

        {/* headline */}
        <h1 className="mt-10 text-[clamp(2.9rem,9vw,7.5rem)]">
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

        <div className="mt-10 border-t border-line" />

        {/* copy + logos */}
        <div className="grid gap-10 pt-10 lg:grid-cols-[1fr_auto] lg:items-start lg:gap-16">
          <div className="enter" style={d(420)}>
            <p className="max-w-md text-[1.15rem] leading-relaxed text-muted">
              Un moteur qui étudie chaque prospect et écrit le message qui fait
              répondre.
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-x-6 gap-y-3">
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

          <div className="enter flex flex-col gap-3" style={d(520)}>
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
      </div>
    </section>
  );
}
