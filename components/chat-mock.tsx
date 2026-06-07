import { AzulTile } from "./wordmark";

function FromAzul({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-end gap-2.5">
      <AzulTile className="h-7 w-7 shrink-0 text-[0.8rem]" />
      <div className="max-w-[82%] border border-ink/12 bg-white px-3.5 py-2.5 text-[0.85rem] leading-relaxed text-ink">
        {children}
      </div>
    </div>
  );
}

function FromYou({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[82%] bg-cobalt px-3.5 py-2.5 text-[0.85rem] leading-relaxed text-white">
        {children}
      </div>
    </div>
  );
}

export function ChatMock() {
  return (
    <div className="border border-ink bg-paper">
      {/* header */}
      <div className="flex items-center gap-2.5 border-b border-ink/15 bg-white px-4 py-3">
        <AzulTile className="h-7 w-7 text-[0.8rem]" />
        <div className="leading-tight">
          <p className="text-[0.85rem] font-semibold text-ink">Azul</p>
          <p className="flex items-center gap-1.5 text-[0.7rem] text-muted">
            <span className="h-1.5 w-1.5 bg-emerald-500" aria-hidden />
            en ligne
          </p>
        </div>
        <span className="ml-auto text-[0.62rem] font-semibold uppercase tracking-label text-muted/70">
          Slack · WhatsApp · Teams
        </span>
      </div>

      {/* thread */}
      <div className="space-y-3 px-4 py-5">
        <FromYou>
          Azul, lance une campagne sur les Head of Sales de scale-ups SaaS
          françaises (Série A/B). Ton direct, 5 lignes max.
        </FromYou>
        <FromAzul>
          Compris. <span className="font-semibold">≈ 240 profils</span>{" "}
          correspondants. Je lance la recherche et je vous soumets les 5
          premiers messages pour calibrage.
        </FromAzul>
        <FromYou>Le 3ᵉ est trop formel — tutoie-le.</FromYou>
        <FromAzul>Noté. Je garde ce ton pour les profils similaires.</FromAzul>
        <FromAzul>
          Première vague validée et partie. Je vous remonte chaque réponse ici,
          dès qu’elle arrive.
        </FromAzul>
      </div>
    </div>
  );
}
