"use client";

import { useState, type CSSProperties, type ReactElement } from "react";
import { QRCodeSVG } from "qrcode.react";
import { SlackMark, WhatsAppMark, TeamsMark, WideArrow } from "./icons";
import { useLang } from "./lang-provider";

type Channel = "whatsapp" | "slack" | "teams";

/* Placeholder destinations: swap in the real number / OAuth URLs at launch. */
const WHATSAPP_LINK = "https://wa.me/PLACEHOLDER?text=Bonjour%20Azul";
const SLACK_OAUTH_URL =
  "https://slack.com/oauth/v2/authorize?client_id=PLACEHOLDER&scope=PLACEHOLDER";
const TEAMS_OAUTH_URL =
  "https://login.microsoftonline.com/common/adminconsent?client_id=PLACEHOLDER";

const marks: Record<Channel, (props: { className?: string }) => ReactElement> = {
  whatsapp: WhatsAppMark,
  slack: SlackMark,
  teams: TeamsMark,
};

function ChannelCard({
  channel,
  index,
  name,
  desc,
  selected,
  onSelect,
}: {
  channel: Channel;
  index: number;
  name: string;
  desc: string;
  selected: boolean;
  onSelect: () => void;
}) {
  const Mark = marks[channel];
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={selected}
      className={`group relative flex h-full flex-col p-6 text-left transition-colors duration-150 sm:p-7 ${
        selected ? "bg-panel" : "bg-paper hover:bg-panel"
      }`}
    >
      {/* selection marker: a cobalt bar, in the step-tile spirit */}
      <span
        aria-hidden
        className={`absolute inset-x-0 top-0 h-[3px] bg-cobalt transition-opacity duration-150 ${
          selected ? "opacity-100" : "opacity-0"
        }`}
      />
      <div className="flex items-center justify-between">
        <Mark className="h-9 w-9" />
        <span
          className={`font-mono text-[0.7rem] uppercase tracking-label ${
            selected ? "text-cobalt" : "text-muted"
          }`}
        >
          {`0${index + 1}`}
        </span>
      </div>
      <h2 className="mt-6 font-display text-[1.3rem] font-bold tracking-[-0.01em] text-ink">
        {name}
      </h2>
      <p className="mt-1.5 text-[0.92rem] leading-relaxed text-muted">{desc}</p>
      <span
        className={`mt-5 inline-flex items-center gap-2 text-[0.82rem] font-semibold transition-colors ${
          selected ? "text-cobalt" : "text-ink/55 group-hover:text-ink"
        }`}
      >
        <span
          aria-hidden
          className={`inline-block h-2 w-2 border border-ink ${
            selected ? "bg-cobalt" : "bg-transparent"
          }`}
        />
        <WideArrow className="h-2.5 w-5" />
      </span>
    </button>
  );
}

export function ConnectChannels() {
  const { t } = useLang();
  const c = t.connect;
  const [selected, setSelected] = useState<Channel | null>(null);
  const order: Channel[] = ["whatsapp", "slack", "teams"];

  return (
    <section className="shell flex flex-1 flex-col justify-center py-14 sm:py-20">
      {/* heading: the landing's voice, lowered — one decision, one cobalt word */}
      <div className="max-w-3xl">
        <span className="label enter" style={{ "--d": "0ms" } as CSSProperties}>
          <span className="sq" />
          {c.tag} · {c.step}
        </span>
        <h1
          className="enter mt-5 font-display text-[clamp(2rem,4.8vw,3.6rem)] font-black leading-[1.02] tracking-[-0.02em] text-ink"
          style={{ "--d": "100ms" } as CSSProperties}
        >
          {c.hPre}
          <span className="text-cobalt">{c.hAccent}</span>
        </h1>
        <p
          className="enter mt-5 max-w-md text-[1.05rem] leading-relaxed text-muted"
          style={{ "--d": "220ms" } as CSSProperties}
        >
          {c.sub}
        </p>
      </div>

      {/* the three channels, in the spec-sheet grid of the landing */}
      <div
        className="enter mt-10 grid gap-px border border-ink/15 bg-ink/15 sm:grid-cols-3"
        style={{ "--d": "320ms" } as CSSProperties}
      >
        {order.map((channel, i) => (
          <ChannelCard
            key={channel}
            channel={channel}
            index={i}
            name={c.channels[channel].name}
            desc={c.channels[channel].desc}
            selected={selected === channel}
            onSelect={() => setSelected(channel)}
          />
        ))}
      </div>

      {/* action panel: re-enters on every change of mind */}
      <div className="enter mt-8" style={{ "--d": "420ms" } as CSSProperties}>
        {selected === null ? (
          <div className="grid-paper flex min-h-[8.5rem] items-center border border-line bg-panel px-6 sm:px-8">
            <p className="font-mono text-[0.74rem] uppercase tracking-[0.14em] text-muted">
              <span className="text-ink">azul</span> // {c.pick}
              <span
                aria-hidden
                className="ml-1.5 inline-block h-[0.78em] w-[7px] translate-y-[0.08em] animate-blink bg-cobalt align-baseline"
              />
            </p>
          </div>
        ) : (
          <div
            key={selected}
            role="region"
            aria-live="polite"
            className="enter border-2 border-ink bg-panel p-7 shadow-hard-cobalt sm:p-9"
          >
            {selected === "whatsapp" && (
              <div className="flex flex-col items-center gap-8 sm:flex-row sm:items-center sm:gap-12">
                <div className="shrink-0 border-2 border-ink bg-white p-4">
                  <QRCodeSVG
                    value={WHATSAPP_LINK}
                    size={184}
                    level="M"
                    bgColor="#FFFFFF"
                    fgColor="#111114"
                    aria-label="QR code WhatsApp"
                  />
                </div>
                <div className="flex flex-col items-center gap-5 sm:items-start">
                  <span className="label">
                    <span className="sq" />
                    {c.waScan}
                  </span>
                  <a
                    href={WHATSAPP_LINK}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-outline"
                  >
                    {c.waOpen}
                    <WideArrow className="h-2.5 w-5" />
                  </a>
                </div>
              </div>
            )}

            {selected === "slack" && (
              <div className="flex flex-col items-start gap-6">
                <span className="label">
                  <span className="sq" />
                  {c.channels.slack.desc}
                </span>
                <a href={SLACK_OAUTH_URL} className="btn">
                  <span className="inline-flex h-6 w-6 items-center justify-center bg-white p-1">
                    <SlackMark className="h-full w-full" />
                  </span>
                  {c.slackBtn}
                  <WideArrow className="h-3 w-6" />
                </a>
              </div>
            )}

            {selected === "teams" && (
              <div className="flex flex-col items-start gap-6">
                <span className="label">
                  <span className="sq" />
                  {c.channels.teams.desc}
                </span>
                <a href={TEAMS_OAUTH_URL} className="btn">
                  <span className="inline-flex h-6 w-6 items-center justify-center bg-white p-1">
                    <TeamsMark className="h-full w-full" />
                  </span>
                  {c.teamsBtn}
                  <WideArrow className="h-3 w-6" />
                </a>
              </div>
            )}
          </div>
        )}
      </div>

      {/* the deliberate non-decision: Outlook comes later, in the thread */}
      <div
        className="enter mt-8 flex items-start gap-3.5 border border-line bg-panel p-5 sm:p-6"
        style={{ "--d": "520ms" } as CSSProperties}
      >
        <span className="sq mt-[0.45rem]" aria-hidden />
        <p className="text-[0.95rem] leading-relaxed text-muted">
          <span className="font-semibold text-ink">{c.noteLabel}</span> {c.note}
        </p>
      </div>
    </section>
  );
}
