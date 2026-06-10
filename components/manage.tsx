"use client";

import { AzulTile } from "./wordmark";
import { SlackMark, WhatsAppMark, TeamsMark, Check } from "./icons";
import { Reveal } from "./reveal";
import { useLang } from "./lang-provider";

export function Manage() {
  const { t } = useLang();
  const m = t.manage;
  return (
    <section id="manage" className="border-t border-line bg-panel">
      <div className="shell grid gap-12 py-20 sm:py-28 lg:grid-cols-[0.92fr_1.08fr] lg:items-center lg:gap-16">
        {/* copy */}
        <Reveal>
          <span className="label">
            <span className="sq" />
            {m.tag}
          </span>
          <h2 className="mt-5 text-balance text-[clamp(1.9rem,4.4vw,3rem)] font-display font-black leading-[1.02] tracking-[-0.015em] text-ink">
            {m.hPre}
            <span className="text-cobalt">{m.hAccent}</span>
          </h2>
          <p className="mt-5 max-w-md text-[1.05rem] leading-relaxed text-muted">
            {m.sub}
          </p>
          <ul className="mt-7 space-y-3.5">
            {m.points.map((point) => (
              <li key={point} className="flex items-start gap-3 text-[0.98rem] text-ink/85">
                <Check className="mt-0.5 h-[1.15rem] w-[1.15rem] shrink-0 text-cobalt" />
                {point}
              </li>
            ))}
          </ul>
        </Reveal>

        {/* the management thread, made tangible */}
        <Reveal delay={90}>
          <div className="border-2 border-ink bg-paper shadow-[6px_6px_0_0_#111114]">
            {/* thread header */}
            <div className="flex items-center gap-3 border-b border-line px-5 py-3.5">
              <AzulTile className="h-9 w-9 text-[0.85rem]" />
              <div className="min-w-0 leading-tight">
                <p className="text-[0.92rem] font-semibold text-ink">Azul</p>
                <p className="font-mono text-[0.6rem] uppercase tracking-label text-muted">
                  {m.role}
                </p>
              </div>
              <span className="ml-auto flex items-center gap-2.5 text-muted/80">
                <SlackMark className="h-[1.15rem] w-[1.15rem]" />
                <WhatsAppMark className="h-[1.15rem] w-[1.15rem]" />
                <TeamsMark className="h-[1.15rem] w-[1.15rem]" />
              </span>
            </div>

            {/* thread */}
            <div className="flex flex-col gap-4 px-5 py-5">
              {m.thread.map((msg, i) =>
                msg.from === "you" ? (
                  <div key={i} className="flex flex-col items-end">
                    <span className="mb-1 font-mono text-[0.58rem] uppercase tracking-label text-muted">
                      {m.you}
                    </span>
                    <p className="max-w-[86%] bg-ink px-3.5 py-2.5 text-[0.85rem] leading-relaxed text-paper">
                      {msg.text}
                    </p>
                  </div>
                ) : (
                  <div key={i} className="flex flex-col items-start">
                    <span className="mb-1 inline-flex items-center gap-1.5 font-mono text-[0.58rem] uppercase tracking-label text-cobalt">
                      <span className="sq" />
                      Azul
                    </span>
                    <p className="max-w-[86%] border border-ink/15 bg-white px-3.5 py-2.5 text-[0.85rem] leading-relaxed text-ink/90">
                      {msg.text}
                    </p>
                  </div>
                ),
              )}
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
