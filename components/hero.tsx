"use client";

import type { CSSProperties, ReactNode } from "react";
import {
  SlackMark,
  WhatsAppMark,
  TeamsMark,
  MailMark,
  LinkedInMark,
  WideArrow,
} from "./icons";
import LiquidMetal from "./liquid-metal";
import BackgroundRippleEffect from "./background-ripple-effect";
import { useLang } from "./lang-provider";

function d(ms: number): CSSProperties {
  return { "--d": `${ms}ms` } as CSSProperties;
}

function ChannelLogo({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <span className="inline-flex items-center gap-2.5 text-[1.02rem] font-medium text-ink/80">
      <span className="text-ink">{icon}</span>
      {label}
    </span>
  );
}

function LiquidBlob() {
  return (
    <div className="relative mx-auto aspect-square w-full max-w-[360px]">
      <LiquidMetal />
    </div>
  );
}

export function Hero() {
  const { t } = useLang();
  return (
    <section id="top" className="relative overflow-hidden border-b border-line">
      <div aria-hidden className="absolute inset-0 z-0">
        <BackgroundRippleEffect rows={14} cols={30} />
      </div>

      {/* content sits above the ripple (z-10); pointer-events pass through to the
          grid, except on the interactive elements (re-enabled below) */}
      <div className="shell pointer-events-none relative z-10 pb-14 pt-6 lg:pb-20">
        {/* system bar */}
        <div
          className="enter flex items-center justify-between border-b border-line py-3 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-muted"
          style={d(0)}
        >
          <span>
            <span className="text-ink">azul</span> {t.hero.sysPost}
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            {t.hero.sysActive}
          </span>
        </div>

        {/* headline + blob */}
        <div className="grid items-center gap-10 pt-12 lg:grid-cols-[1.05fr_minmax(300px,380px)] lg:gap-14 lg:pt-16">
          <div>
            <h1 className="text-[clamp(2.3rem,5.4vw,4.4rem)]">
              <span className="rise-wrap">
                <span className="rise display text-ink" style={d(120)}>
                  {t.hero.h1a}
                </span>
              </span>
              <span className="rise-wrap">
                <span className="rise display text-cobalt" style={d(240)}>
                  {t.hero.h1b}
                </span>
              </span>
            </h1>

            <p
              className="enter mt-6 max-w-md text-[1.08rem] leading-relaxed text-muted"
              style={d(420)}
            >
              {t.hero.sub}
            </p>

            <div
              className="enter mt-8 flex flex-wrap items-center gap-x-7 gap-y-4"
              style={d(520)}
            >
              <a href="#waitlist" className="btn pointer-events-auto">
                {t.cta}
                <WideArrow className="h-3 w-7" />
              </a>
              <a
                href="#problem"
                className="group pointer-events-auto inline-flex items-center gap-2.5 text-[0.95rem] font-semibold text-ink transition-colors hover:text-cobalt"
              >
                {t.hero.why}
                <WideArrow className="h-3 w-6 transition-transform duration-200 group-hover:translate-x-1.5" />
              </a>
            </div>
          </div>

          <a
            href="#waitlist"
            aria-label={t.hero.blobAria}
            className="enter pointer-events-auto block cursor-pointer transition-transform duration-300 hover:scale-[1.02]"
            style={d(440)}
          >
            <LiquidBlob />
          </a>
        </div>

        {/* channel logos */}
        <div
          className="enter mt-12 flex flex-col gap-4 border-t border-line pt-7 sm:flex-row sm:items-center sm:justify-between"
          style={d(620)}
        >
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2.5">
            <span className="font-mono text-[0.8rem] uppercase tracking-[0.14em] text-muted">
              {t.hero.pilotedFrom}
            </span>
            <ChannelLogo icon={<SlackMark className="h-[1.35rem] w-[1.35rem]" />} label="Slack" />
            <ChannelLogo icon={<WhatsAppMark className="h-[1.35rem] w-[1.35rem]" />} label="WhatsApp" />
            <ChannelLogo icon={<TeamsMark className="h-[1.35rem] w-[1.35rem]" />} label="Teams" />
          </div>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2.5">
            <span className="font-mono text-[0.8rem] uppercase tracking-[0.14em] text-muted">
              {t.hero.prospectsVia}
            </span>
            <ChannelLogo icon={<MailMark className="h-[1.35rem] w-[1.35rem]" />} label="Email" />
            <ChannelLogo icon={<LinkedInMark className="h-[1.35rem] w-[1.35rem]" />} label="LinkedIn" />
          </div>
        </div>
      </div>
    </section>
  );
}
