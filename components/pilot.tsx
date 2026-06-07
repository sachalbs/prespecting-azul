import { ChatMock } from "./chat-mock";
import { Reveal } from "./reveal";
import { Spark, Check, Reply } from "./icons";

const points = [
  {
    icon: <Spark className="h-[1.1rem] w-[1.1rem]" />,
    title: "Vous le briefez en langage naturel",
    desc: "« Lance une campagne sur… » — et c’est parti. Aucune syntaxe à apprendre.",
  },
  {
    icon: <Check className="h-[1.1rem] w-[1.1rem]" />,
    title: "Vous gardez la main",
    desc: "Vous validez les premiers messages, vous le corrigez, il calibre le reste.",
  },
  {
    icon: <Reply className="h-[1.1rem] w-[1.1rem]" />,
    title: "Il vous rend des comptes",
    desc: "Avancement et réponses arrivent directement dans votre fil de discussion.",
  },
];

export function Pilot() {
  return (
    <section id="pilot" className="relative overflow-hidden bg-ink text-white">
      <div aria-hidden className="blueprint pointer-events-none absolute inset-0 opacity-80" />
      <div className="shell relative py-20 sm:py-28">
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
          {/* copy */}
          <div className="max-w-xl">
            <Reveal>
              <span className="label !text-cobalt-300">
                <span className="text-white">02</span> / Le pilotage
              </span>
              <h2 className="mt-5 text-[clamp(1.9rem,4.2vw,2.9rem)] font-display font-black leading-[1.04] tracking-[-0.015em] text-white">
                Vous le managez comme un employé. Depuis vos propres outils.
              </h2>
              <p className="mt-5 text-[1.05rem] leading-relaxed text-white/60">
                Aucun tableau de bord, aucune appli à apprendre. Il vit dans
                Slack, WhatsApp ou Teams, et prospecte par email et LinkedIn.
              </p>
            </Reveal>

            <Reveal delay={90}>
              <ul className="mt-9 space-y-6">
                {points.map((p) => (
                  <li key={p.title} className="flex gap-4">
                    <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center border border-white/15 bg-white/5 text-cobalt-300">
                      {p.icon}
                    </span>
                    <div>
                      <p className="font-semibold text-white">{p.title}</p>
                      <p className="mt-1 text-[0.95rem] leading-relaxed text-white/55">
                        {p.desc}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            </Reveal>

            <Reveal delay={150}>
              <p className="mt-9 border-t border-white/12 pt-6 text-[0.72rem] font-semibold uppercase tracking-label text-white/50">
                <span className="text-white">Piloté depuis</span> — Slack ·
                WhatsApp · Teams
              </p>
            </Reveal>
          </div>

          {/* chat */}
          <Reveal delay={120}>
            <ChatMock />
          </Reveal>
        </div>
      </div>
    </section>
  );
}
