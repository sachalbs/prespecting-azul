import { Reveal } from "./reveal";

export function Metric() {
  return (
    <section className="relative overflow-hidden bg-cobalt text-white">
      <div aria-hidden className="blueprint pointer-events-none absolute inset-0 opacity-60" />
      <div className="shell relative py-20 sm:py-28">
        <Reveal className="max-w-4xl">
          <span className="label !text-white/70">
            <span className="h-2 w-2 bg-white" />
            La seule métrique qui compte
          </span>
          <p className="mt-6 text-[clamp(2.1rem,5.4vw,3.8rem)] font-display font-black uppercase leading-[0.98] tracking-[-0.02em] text-white">
            Le taux de réponse.
            <br />
            <span className="text-white/55">Pas le volume d’envois.</span>
          </p>
          <div className="mt-9 max-w-xl border-t border-white/25 pt-6">
            <p className="text-[1.05rem] leading-relaxed text-white/80">
              Tout le produit est construit autour d’une seule question :
              est-ce que vos prospects répondent ? Le volume, les cadences, les
              « séquences » ne sont que des moyens. Azul optimise la fin, pas le
              bruit.
            </p>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
