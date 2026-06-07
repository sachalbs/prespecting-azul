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
    <section className="shell py-20 sm:py-28">
      <Reveal className="max-w-3xl">
        <span className="label">
          <span className="sq" />
          Le problème
        </span>
        <h2 className="mt-5 text-[clamp(1.9rem,4.4vw,3rem)] font-display font-black leading-[1.02] tracking-[-0.015em] text-ink">
          L’outbound n’est pas saturé d’outils. Il est saturé de messages
          génériques.
        </h2>
        <p className="mt-5 max-w-2xl text-[1.08rem] leading-relaxed text-muted">
          La première vague de « SDR IA » a optimisé le volume : prospects
          grillés, réputation d’envoi abîmée, taux de réponse en chute. Azul
          prend le problème à l’envers.
        </p>
      </Reveal>

      <div className="mt-12 grid items-start gap-5 lg:grid-cols-2">
        {/* the old way */}
        <Reveal>
          <div className="border border-ink/15 bg-paper p-7">
            <span className="label">L’approche au volume</span>
            <ul className="mt-6 space-y-4">
              {oldWay.map((item) => (
                <li
                  key={item}
                  className="flex items-start gap-3 text-[0.98rem] text-muted"
                >
                  <Cross className="mt-0.5 h-[1.1rem] w-[1.1rem] shrink-0 text-muted/50" />
                  <span className="line-through decoration-ink/20">{item}</span>
                </li>
              ))}
            </ul>
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
