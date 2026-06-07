import { ResearchConsole } from "./research-console";
import { ArrowRight } from "./icons";
import type { CSSProperties } from "react";

function d(ms: number): CSSProperties {
  return { "--d": `${ms}ms` } as CSSProperties;
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

        {/* main */}
        <div className="grid items-center gap-12 pt-12 lg:grid-cols-[1fr_minmax(360px,440px)] lg:gap-14 lg:pt-16">
          <div>
            <h1 className="text-[clamp(2.8rem,8.6vw,7rem)]">
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
              className="enter mt-7 max-w-md text-[1.12rem] leading-relaxed text-muted"
              style={d(440)}
            >
              Un moteur qui étudie chaque prospect et écrit le message qui fait
              répondre.
            </p>

            <div
              className="enter mt-8 flex flex-wrap items-center gap-x-6 gap-y-3"
              style={d(560)}
            >
              <a href="#waitlist" className="btn">
                Rejoindre la liste
                <ArrowRight className="h-4 w-4" />
              </a>
              <a
                href="#how"
                className="font-mono text-[0.74rem] font-medium uppercase tracking-[0.14em] text-muted transition-colors hover:text-ink"
              >
                ▸ voir comment ça marche
              </a>
            </div>
          </div>

          {/* the engine */}
          <div className="enter" style={d(500)}>
            <ResearchConsole />
          </div>
        </div>

        {/* meta strip */}
        <div
          className="enter mt-14 flex flex-col gap-3 border-t border-line pt-6 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-muted sm:flex-row sm:items-center sm:justify-between"
          style={d(680)}
        >
          <span>
            <span className="text-ink">piloté depuis</span> — slack · whatsapp ·
            teams
          </span>
          <span>
            <span className="text-ink">prospecte via</span> — email · linkedin
          </span>
        </div>
      </div>
    </section>
  );
}
