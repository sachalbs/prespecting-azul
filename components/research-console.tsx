import type { CSSProperties } from "react";

const steps: { k: string; v: string }[] = [
  { k: "levées", v: "Série A · il y a 3 sem." },
  { k: "recrutements", v: "4 postes SDR ouverts" },
  { k: "stack", v: "HubSpot + Apollo" },
  { k: "signaux", v: "a publié sur l’outbound" },
  { k: "rédaction", v: "message référencé prêt" },
];

function d(ms: number): CSSProperties {
  return { "--d": `${ms}ms` } as CSSProperties;
}

/** The "engine": a live readout of Azul researching one prospect, end to end.
 *  Monospace, precise, sequential — the proof that real work happens per lead. */
export function ResearchConsole() {
  return (
    <div className="border border-ink bg-ink font-mono text-[0.8rem] text-paper shadow-hard-cobalt">
      {/* status bar */}
      <div className="flex items-center justify-between border-b border-white/12 px-4 py-2.5">
        <span className="text-white/90">azul · moteur</span>
        <span className="inline-flex items-center gap-1.5 text-emerald-400">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          analyse
        </span>
      </div>

      {/* readout */}
      <div className="space-y-2 px-4 py-4">
        <div className="term-step flex items-center" style={d(220)}>
          <span className="shrink-0 text-white/40">cible</span>
          <span className="mx-2 flex-1 border-b border-dotted border-white/15" />
          <span className="shrink-0 text-white">Camille Roche · Head of Sales</span>
        </div>

        {steps.map((s, i) => (
          <div
            key={s.k}
            className="term-step flex items-center"
            style={d(520 + i * 280)}
          >
            <span className="shrink-0 text-white/40">{s.k}</span>
            <span className="mx-2 flex-1 border-b border-dotted border-white/15" />
            <span className="shrink-0 text-cobalt-300">✓</span>
            <span className="ml-1.5 shrink-0 text-white/90">{s.v}</span>
          </div>
        ))}
      </div>

      {/* footer */}
      <div
        className="term-step flex items-center gap-1 border-t border-white/12 px-4 py-2.5 text-white/55"
        style={d(520 + steps.length * 280)}
      >
        <span>└ message prêt — en attente de votre validation</span>
        <span className="ml-0.5 inline-block h-3.5 w-[0.5ch] bg-cobalt-400 animate-blink" aria-hidden />
      </div>
    </div>
  );
}
