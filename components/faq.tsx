"use client";

import { Reveal } from "./reveal";
import { useLang } from "./lang-provider";

export function Faq() {
  const { t } = useLang();
  const f = t.faq;
  return (
    <section id="faq" className="shell py-20 sm:py-28">
      <Reveal className="max-w-3xl">
        <span className="label">
          <span className="sq" />
          {f.tag}
        </span>
        <h2 className="mt-5 text-balance text-[clamp(1.9rem,4.4vw,3rem)] font-display font-black leading-[1.02] tracking-[-0.015em] text-ink">
          {f.hPre}
          <span className="text-cobalt">{f.hAccent}</span>
        </h2>
      </Reveal>

      <div className="mt-10 max-w-3xl border-t border-ink/15">
        {f.items.map((item, i) => (
          <Reveal key={item.q} delay={i * 55}>
            <details className="faq-item border-b border-ink/15" {...(i === 0 ? { open: true } : {})}>
              <summary className="faq-summary flex cursor-pointer list-none items-center justify-between gap-6 py-5 text-[1.05rem] font-semibold text-ink transition-colors hover:text-cobalt">
                {item.q}
                <svg
                  className="faq-icon h-4 w-4 shrink-0 text-cobalt transition-transform duration-200"
                  viewBox="0 0 16 16"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                  strokeLinecap="round"
                  aria-hidden
                >
                  <path d="M8 1.5v13M1.5 8h13" />
                </svg>
              </summary>
              <p className="max-w-2xl pb-6 text-[1rem] leading-relaxed text-muted">
                {item.a}
              </p>
            </details>
          </Reveal>
        ))}
      </div>
    </section>
  );
}
