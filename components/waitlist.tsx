"use client";

import { WaitlistTrigger } from "./waitlist-trigger";
import { WideArrow } from "./icons";
import { Reveal } from "./reveal";
import { useLang } from "./lang-provider";

export function Waitlist() {
  const { t } = useLang();
  return (
    <section id="waitlist" className="shell py-20 sm:py-28">
      <Reveal>
        <div className="grid gap-10 border border-ink bg-panel p-7 sm:p-12 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:gap-16">
          {/* copy */}
          <div>
            <span className="label">
              <span className="text-cobalt">03</span> / {t.waitlist.tag}
            </span>
            <h2 className="mt-5 display text-[clamp(2rem,5vw,3.4rem)] text-ink">
              {t.waitlist.h}
            </h2>
            <p className="mt-5 max-w-lg text-[1.05rem] leading-relaxed text-muted">
              {t.waitlist.sub}
            </p>
          </div>

          {/* waitlist CTA — opens the Typeform popup */}
          <div>
            <WaitlistTrigger className="btn w-full justify-center sm:w-auto">
              {t.cta}
              <WideArrow className="h-3 w-7" />
            </WaitlistTrigger>
            <p className="mt-4 text-[0.83rem] text-muted">{t.waitlist.note}</p>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
