import { Reveal } from "./reveal";
import { Search, Pen, Loop } from "./icons";

const steps = [
  {
    n: "01",
    icon: <Search className="h-5 w-5" />,
    title: "Recherche",
    desc: "Levées, recrutements, stack, signaux d’intérêt. Du contexte réel, pas une variable {{prénom}}.",
  },
  {
    n: "02",
    icon: <Pen className="h-5 w-5" />,
    title: "Rédaction",
    desc: "Un message personnel et référencé, calé sur votre offre et votre ton. Jamais robot.",
  },
  {
    n: "03",
    icon: <Loop className="h-5 w-5" />,
    title: "Envoi & apprentissage",
    desc: "Vous validez les premiers, il calibre le reste, envoie et s’améliore campagne après campagne.",
  },
];

export function HowItWorks() {
  return (
    <section id="how" className="shell py-20 sm:py-28">
      <Reveal className="max-w-3xl">
        <span className="label">
          <span className="sq" />
          Comment ça marche
        </span>
        <h2 className="mt-5 text-[clamp(1.9rem,4.4vw,3rem)] font-display font-black leading-[1.02] tracking-[-0.015em] text-ink">
          De la recherche à la réponse, en trois temps.
        </h2>
      </Reveal>

      <div className="mt-12 grid gap-px border border-ink/15 bg-ink/15 sm:grid-cols-3">
        {steps.map((step, i) => (
          <Reveal key={step.n} delay={i * 90} className="bg-paper">
            <div className="flex h-full flex-col p-7">
              <div className="flex items-center justify-between">
                <span className="font-display text-[2.5rem] font-black leading-none text-cobalt">
                  {step.n}
                </span>
                <span className="flex h-10 w-10 items-center justify-center border border-ink/15 text-ink">
                  {step.icon}
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
