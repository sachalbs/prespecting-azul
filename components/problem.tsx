import { Reveal } from "./reveal";
import { Cross } from "./icons";
import { MessageCard } from "./message-card";

const oldWay = [
  "Templates à peine personnalisés",
  "Toujours plus d’envois",
  "Prospects grillés, réputation abîmée",
  "On mesure le volume",
];

export function Problem() {
  return (
    <section id="problem" className="shell py-20 sm:py-28">
      <Reveal className="max-w-3xl">
        <span className="label">
          <span className="text-cobalt">01</span> / Le problème
        </span>
        <h2 className="mt-5 text-[clamp(1.9rem,4.4vw,3rem)] font-display font-black leading-[1.02] tracking-[-0.015em] text-ink">
          Vos prospects sont saturés de messages{" "}
          <span className="text-cobalt">génériques.</span>
        </h2>
        <p className="mt-5 max-w-2xl text-[1.08rem] leading-relaxed text-muted">
          La première vague de « SDR IA » a optimisé le volume. Azul prend le
          problème à l’envers.
        </p>
      </Reveal>

      <div className="mt-12 grid items-start gap-5 lg:grid-cols-2">
        {/* the old way */}
        <Reveal>
          <div className="caution-stripes flex h-full flex-col border border-ink/10 bg-ink/[0.02] p-7">
            <span className="label !text-red-500/80">
              <Cross className="h-[0.9rem] w-[0.9rem]" />
              L’approche au volume
            </span>
            <ul className="mt-6 space-y-4">
              {oldWay.map((item) => (
                <li
                  key={item}
                  className="flex items-start gap-3 text-[0.98rem] text-muted"
                >
                  <Cross className="mt-0.5 h-[1.1rem] w-[1.1rem] shrink-0 text-red-400/80" />
                  <span className="line-through decoration-ink/20">{item}</span>
                </li>
              ))}
            </ul>
            <p className="mt-auto border-t border-ink/10 pt-5 text-[0.95rem] font-semibold text-red-500/90">
              → Résultat : vous finissez en spam.
            </p>
          </div>
        </Reveal>

        {/* the Azul way, made tangible */}
        <Reveal delay={90}>
          <span className="label mb-3">
            <span className="sq" />
            L’approche d’Azul — un message écrit pour Camille
          </span>
          <MessageCard />
        </Reveal>
      </div>
    </section>
  );
}
