import type { CSSProperties, ReactNode } from "react";
import { ResearchConsole } from "./research-console";
import {
  ArrowRight,
  SlackMark,
  WhatsAppMark,
  TeamsMark,
  MailMark,
  LinkedInMark,
} from "./icons";

// Aluminium-shape background video (plays live on Vercel / in the browser; the
// preview sandbox can't reach this host, so the CSS brushed-metal layer shows
// underneath instead). Swap this URL to change the clip.
const VIDEO_SRC =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260518_003132_8b7edcb6-c64d-4a52-a9ca-879942e122ad.mp4";

function d(ms: number): CSSProperties {
  return { "--d": `${ms}ms` } as CSSProperties;
}

function ChannelLogo({ icon, label }: { icon: ReactNode; label: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-white/85">
      <span className="text-white">{icon}</span>
      <span className="text-[0.9rem] font-medium">{label}</span>
    </span>
  );
}

export function Hero() {
  return (
    <section
      id="top"
      className="relative isolate overflow-hidden bg-ink text-white"
    >
      {/* brushed aluminium base + animated light sweep (also the video fallback) */}
      <div aria-hidden className="metal-bg metal-sweep absolute inset-0" />
      {/* the aluminium-shape video */}
      <video
        className="absolute inset-0 h-full w-full object-cover opacity-85"
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
        aria-hidden
      >
        <source src={VIDEO_SRC} type="video/mp4" />
      </video>
      {/* legibility scrim — light so the metal still reads through the blend */}
      <div
        aria-hidden
        className="absolute inset-0 bg-gradient-to-b from-ink/25 via-transparent to-ink/80"
      />

      <div className="shell relative flex min-h-[88vh] flex-col py-7">
        {/* system bar */}
        <div
          className="fade-in flex items-center justify-between border-b border-white/15 py-3 font-mono text-[0.7rem] uppercase tracking-[0.14em] text-white/70"
          style={d(0)}
        >
          <span>
            <span className="text-white">azul</span> // moteur de prospection
            autonome
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
            système actif
          </span>
        </div>

        {/* center */}
        <div className="flex flex-1 items-center">
          <div className="grid w-full items-center gap-12 py-14 lg:grid-cols-[1fr_minmax(340px,420px)] lg:gap-14">
            <div className="fade-in" style={d(140)}>
              <h1 className="blend-text text-[clamp(2.8rem,8.6vw,7rem)]">
                <span className="display block">Le bon message,</span>
                <span className="display block">au bon prospect.</span>
              </h1>
              <p className="mt-7 max-w-md text-[1.12rem] leading-relaxed text-white/80">
                Un moteur qui étudie chaque prospect et écrit le message qui
                fait répondre.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-x-6 gap-y-3">
                <a href="#waitlist" className="btn">
                  Rejoindre la liste
                  <ArrowRight className="h-4 w-4" />
                </a>
                <a
                  href="#problem"
                  className="font-mono text-[0.74rem] font-medium uppercase tracking-[0.14em] text-white/70 transition-colors hover:text-white"
                >
                  ▸ pourquoi azul
                </a>
              </div>
            </div>

            <div className="fade-in" style={d(380)}>
              <ResearchConsole />
            </div>
          </div>
        </div>

        {/* the right logos */}
        <div
          className="fade-in flex flex-col gap-4 border-t border-white/15 pt-6 sm:flex-row sm:items-center sm:justify-between"
          style={d(520)}
        >
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
            <span className="font-mono text-[0.7rem] uppercase tracking-[0.14em] text-white/55">
              Piloté depuis
            </span>
            <ChannelLogo icon={<SlackMark className="h-[1.15rem] w-[1.15rem]" />} label="Slack" />
            <ChannelLogo icon={<WhatsAppMark className="h-[1.15rem] w-[1.15rem]" />} label="WhatsApp" />
            <ChannelLogo icon={<TeamsMark className="h-[1.15rem] w-[1.15rem]" />} label="Teams" />
          </div>
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
            <span className="font-mono text-[0.7rem] uppercase tracking-[0.14em] text-white/55">
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
