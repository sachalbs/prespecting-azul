"use client";

import { useEffect, useRef, useState } from "react";

const CELL = 54;

/** Interactive "ripple" grid: cells near the cursor light up with a delay
 *  proportional to their distance, so a wave radiates out. Native reproduction
 *  of the Framer BackgroundRippleEffect. */
export function BackgroundRipple() {
  const ref = useRef<HTMLDivElement>(null);
  const [dim, setDim] = useState({ cols: 0, rows: 0 });
  const [src, setSrc] = useState<{ r: number; c: number } | null>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const measure = () => {
      const r = el.getBoundingClientRect();
      setDim({
        cols: Math.max(1, Math.ceil(r.width / CELL)),
        rows: Math.max(1, Math.ceil(r.height / CELL)),
      });
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const cells = dim.cols * dim.rows;

  return (
    <div ref={ref} aria-hidden className="absolute inset-0 overflow-hidden">
      <div
        className="grid h-full w-full"
        style={{
          gridTemplateColumns: `repeat(${dim.cols}, minmax(0, 1fr))`,
          gridTemplateRows: `repeat(${dim.rows}, minmax(0, 1fr))`,
        }}
        onMouseLeave={() => setSrc(null)}
      >
        {Array.from({ length: cells }).map((_, i) => {
          const r = Math.floor(i / dim.cols);
          const c = i % dim.cols;
          const dist = src ? Math.hypot(r - src.r, c - src.c) : 99;
          const lit = src !== null && dist < 3.2;
          return (
            <div
              key={i}
              onMouseEnter={() => setSrc({ r, c })}
              className="border border-ink/[0.045] transition-colors duration-500 ease-out"
              style={{
                transitionDelay: src ? `${dist * 55}ms` : "0ms",
                backgroundColor: lit ? "rgba(44, 78, 230, 0.1)" : "transparent",
              }}
            />
          );
        })}
      </div>
    </div>
  );
}
