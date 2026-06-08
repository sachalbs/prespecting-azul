"use client";

import { MailMark, LinkedInMark } from "./icons";
import { useLang } from "./lang-provider";

function Signal({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 border border-ink/15 bg-white px-2.5 py-1 text-[0.72rem] font-medium text-ink/80">
      <span className="sq" />
      {children}
    </span>
  );
}

function Ref({ children }: { children: React.ReactNode }) {
  return (
    <span className="bg-cobalt/12 px-0.5 font-medium text-ink">{children}</span>
  );
}

/** A researched, referenced outbound message, shown as a draft awaiting the
 *  user's approval (the human-in-the-loop the brief describes). */
export function MessageCard() {
  const { t } = useLang();
  const c = t.card;
  return (
    <figure className="border-2 border-ink bg-panel shadow-[6px_6px_0_0_#2C4EE6]">
      {/* recipient */}
      <div className="flex items-center gap-3 border-b border-line px-5 py-4">
        <span className="flex h-10 w-10 items-center justify-center bg-ink font-display text-[0.85rem] font-bold text-paper">
          CR
        </span>
        <div className="min-w-0">
          <p className="truncate text-[0.95rem] font-semibold text-ink">
            Camille Roche
          </p>
          <p className="truncate text-[0.8rem] text-muted">{c.role}</p>
        </div>
        <span className="label ml-auto !gap-1.5 !text-[0.62rem] text-cobalt">
          <span className="sq" />
          {c.signals}
        </span>
      </div>

      {/* research signals */}
      <div className="flex flex-wrap gap-1.5 px-5 pt-4">
        {c.chips.map((chip) => (
          <Signal key={chip}>{chip}</Signal>
        ))}
      </div>

      {/* message */}
      <div className="px-5 py-4 text-[0.86rem] leading-relaxed text-ink/90">
        <p>{c.greeting}</p>
        {c.bodyLines.map((line, li) => (
          <p key={li} className="mt-3">
            {line.map((seg, si) =>
              si % 2 === 1 ? <Ref key={si}>{seg}</Ref> : seg,
            )}
          </p>
        ))}
      </div>

      {/* draft state + destination channels */}
      <figcaption className="flex items-center justify-between border-t border-line px-5 py-3.5">
        <span className="flex items-center gap-2 text-[0.72rem] font-semibold uppercase tracking-label text-muted">
          <span className="h-2 w-2 bg-amber-500 animate-pulse" aria-hidden />
          {c.draft}
        </span>
        <span className="flex items-center gap-2.5 text-muted/80">
          <MailMark className="h-4 w-4" />
          <LinkedInMark className="h-4 w-4" />
        </span>
      </figcaption>
    </figure>
  );
}
