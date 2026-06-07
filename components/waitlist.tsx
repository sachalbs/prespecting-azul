import { WaitlistForm } from "./waitlist-form";
import { Reveal } from "./reveal";

export function Waitlist() {
  return (
    <section id="waitlist" className="shell py-20 sm:py-28">
      <Reveal>
        <div className="grid gap-10 border border-ink bg-panel p-7 sm:p-12 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:gap-16">
          {/* copy */}
          <div>
            <span className="label">
              <span className="text-cobalt">05</span> / Accès anticipé
            </span>
            <h2 className="mt-5 display text-[clamp(2rem,5vw,3.4rem)] text-ink">
              Rejoignez la liste d’attente.
            </h2>
            <p className="mt-5 max-w-lg text-[1.05rem] leading-relaxed text-muted">
              Accès anticipé. Pas de clients publics ni de chiffres à brandir :
              on construit avec les premières équipes.
            </p>
          </div>

          {/* form */}
          <div>
            <WaitlistForm />
            <p className="text-[0.83rem] text-muted">
              On onboarde par petites vagues, dans l’ordre d’inscription.
            </p>
          </div>
        </div>
      </Reveal>
    </section>
  );
}
