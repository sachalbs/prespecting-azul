import { MailMark, LinkedInMark } from "./icons";

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

/** A researched, referenced outbound message — shown as a draft awaiting the
 *  user's approval (the human-in-the-loop the brief describes). */
export function MessageCard() {
  return (
    <figure className="border border-ink bg-panel">
      {/* recipient */}
      <div className="flex items-center gap-3 border-b border-line px-5 py-4">
        <span className="flex h-10 w-10 items-center justify-center bg-ink font-display text-[0.85rem] font-bold text-paper">
          CR
        </span>
        <div className="min-w-0">
          <p className="truncate text-[0.95rem] font-semibold text-ink">
            Camille Roche
          </p>
          <p className="truncate text-[0.8rem] text-muted">
            Head of Sales · Lumen
          </p>
        </div>
        <span className="label ml-auto !gap-1.5 !text-[0.62rem] text-cobalt">
          <span className="sq" />4 signaux
        </span>
      </div>

      {/* research signals */}
      <div className="flex flex-wrap gap-1.5 px-5 pt-4">
        <Signal>Série A — il y a 3 semaines</Signal>
        <Signal>Recrute 4 SDR</Signal>
        <Signal>HubSpot + Apollo</Signal>
        <Signal>A publié sur l’outbound</Signal>
      </div>

      {/* message */}
      <div className="px-5 py-4">
        <p className="text-[0.86rem] leading-relaxed text-ink/90">
          Bonjour Camille,
          <br />
          <br />
          Votre <Ref>Série A annoncée le mois dernier</Ref> et les{" "}
          <Ref>4 postes de SDR ouverts</Ref> pointent vers la même priorité :
          structurer l’outbound vite, sans le saturer.
          <br />
          <br />
          Vous êtes déjà sur <Ref>HubSpot et Apollo</Ref> — j’ai une approche
          précise en tête pour vos premières séquences. Dix minutes la semaine
          prochaine&nbsp;?
        </p>
      </div>

      {/* draft state + destination channels */}
      <figcaption className="flex items-center justify-between border-t border-line px-5 py-3.5">
        <span className="flex items-center gap-2 text-[0.72rem] font-semibold uppercase tracking-label text-muted">
          <span className="h-2 w-2 bg-amber-500" aria-hidden />
          Brouillon · à valider
        </span>
        <span className="flex items-center gap-2.5 text-muted/80">
          <MailMark className="h-4 w-4" />
          <LinkedInMark className="h-4 w-4" />
        </span>
      </figcaption>
    </figure>
  );
}
