import type { SVGProps } from "react";

// Sober, "spec-sheet" illustrations for the three steps: monochrome ink line-art
// with a single cobalt accent, framed on a faint blueprint-grid tile. Native —
// no external assets.

const wrap = {
  viewBox: "0 0 48 48",
  fill: "none" as const,
  stroke: "currentColor",
  strokeWidth: 1.6,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

// 01 — Research: a radar sweep that locks onto a cobalt signal.
function Radar(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...wrap} {...props}>
      <g opacity="0.5">
        <circle cx="23" cy="25" r="15" />
        <circle cx="23" cy="25" r="8.5" />
        <path d="M23 6v4M23 40v4M4 25h4M38 25h4" />
      </g>
      <path d="M23 25 34 14" className="stroke-cobalt" />
      <circle cx="34" cy="14" r="2.8" className="fill-cobalt" stroke="none" />
    </svg>
  );
}

// 02 — Writing: a draft with a highlighted line and a cobalt cursor.
function Draft(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...wrap} {...props}>
      <g opacity="0.5">
        <rect x="10" y="8" width="28" height="32" rx="2" />
        <path d="M16 25h16M16 31h16M16 37h9" />
      </g>
      <path d="M16 18h13" className="stroke-cobalt" />
      <path d="M30 34v6" className="stroke-cobalt" />
    </svg>
  );
}

// 03 — Send & learn: an outbound signal that broadcasts and iterates.
function Broadcast(props: SVGProps<SVGSVGElement>) {
  return (
    <svg {...wrap} {...props}>
      <g opacity="0.5">
        <path d="M21 16a13 13 0 0 1 0 18" />
        <path d="M16 20a7 7 0 0 1 0 10" />
      </g>
      <circle cx="12" cy="25" r="2.8" className="fill-cobalt" stroke="none" />
      <path d="M27 25h9" className="stroke-cobalt" />
      <path d="M32 20l5 5-5 5" className="stroke-cobalt" />
    </svg>
  );
}

const ART = [Radar, Draft, Broadcast];

const GRID =
  "linear-gradient(to right, rgba(17,17,20,0.05) 1px, transparent 1px)," +
  "linear-gradient(to bottom, rgba(17,17,20,0.05) 1px, transparent 1px)";

export function StepVisual({ index }: { index: number }) {
  const Art = ART[index] ?? Radar;
  return (
    <span
      className="flex h-16 w-16 shrink-0 items-center justify-center border border-ink/15 text-ink"
      style={{ backgroundImage: GRID, backgroundSize: "8px 8px" }}
    >
      <Art className="h-10 w-10" />
    </span>
  );
}
