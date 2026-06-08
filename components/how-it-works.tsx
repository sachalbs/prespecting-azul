"use client";

import { Reveal } from "./reveal";
import { Search, Pen, Loop } from "./icons";
import { useLang } from "./lang-provider";

const icons = [
  <Search key="s" className="h-5 w-5" />,
  <Pen key="p" className="h-5 w-5" />,
  <Loop key="l" className="h-5 w-5" />,
];

export function HowItWorks() {
  const { t } = useLang();
  return (
    <section id="how" className="shell py-20 sm:py-28">
      <Reveal className="max-w-3xl">
        <span className="label">
          <span className="text-cobalt">02</span> / {t.how.tag}
        </span>
        <h2 className="mt-5 text-[clamp(1.9rem,4.4vw,3rem)] font-display font-black leading-[1.02] tracking-[-0.015em] text-ink">
          {t.how.h}
        </h2>
      </Reveal>

      <div className="mt-12 grid gap-px border border-ink/15 bg-ink/15 sm:grid-cols-3">
        {t.how.steps.map((step, i) => (
          <Reveal key={i} delay={i * 90} className="bg-paper">
            <div className="flex h-full flex-col p-7">
              <div className="flex items-center justify-between">
                <span className="font-display text-[2.5rem] font-black leading-none text-cobalt">
                  {`0${i + 1}`}
                </span>
                <span className="flex h-10 w-10 items-center justify-center border border-ink/15 text-ink">
                  {icons[i]}
                </span>
              </div>
              <h3 className="mt-7 font-display text-[1.3rem] font-bold tracking-[-0.01em] text-ink">
                {step.title}
              </h3>
              <p className="mt-2.5 text-[0.96rem] leading-relaxed text-muted">
                {step.desc}
              </p>
            </div>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
