"use client";

import { useEffect, useRef } from "react";

// Native reproduction of a Framer-style "CursorTrail": a comet of small cobalt
// squares that lag behind the pointer, shrinking and fading along the tail.
// Brand-tuned to Azul's ■ motif. Pointer-events-none so it never blocks the UI.

const COUNT = 10;

export default function CursorTrail() {
  const nodesRef = useRef<Array<HTMLDivElement | null>>([]);

  useEffect(() => {
    // Honor reduced-motion; the overlay is also CSS-hidden on touch (see globals).
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const nodes = nodesRef.current.filter(Boolean) as HTMLDivElement[];
    if (nodes.length === 0) return;

    const pts = Array.from({ length: COUNT }, () => ({ x: -100, y: -100 }));
    const mouse = { x: -100, y: -100 };
    let visible = false;
    let raf = 0;

    const onMove = (e: MouseEvent) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
      if (!visible) {
        // Snap the whole trail to the cursor on first move (no streak from 0,0).
        for (const p of pts) {
          p.x = mouse.x;
          p.y = mouse.y;
        }
        visible = true;
      }
    };
    const onLeave = () => {
      visible = false;
    };

    const tick = () => {
      // Head eases toward the pointer; each node eases toward the one before it.
      let px = mouse.x;
      let py = mouse.y;
      for (let i = 0; i < pts.length; i++) {
        const p = pts[i];
        p.x += (px - p.x) * 0.42;
        p.y += (py - p.y) * 0.42;
        const t = i / (COUNT - 1); // 0 = head, 1 = tail
        const size = 8 - t * 6; // 8px → 2px
        const node = nodes[i];
        node.style.width = `${size}px`;
        node.style.height = `${size}px`;
        node.style.opacity = visible ? `${(1 - t) * 0.4}` : "0";
        node.style.transform = `translate(${p.x}px, ${p.y}px) translate(-50%, -50%)`;
        px = p.x;
        py = p.y;
      }
      raf = requestAnimationFrame(tick);
    };

    window.addEventListener("mousemove", onMove);
    document.addEventListener("mouseleave", onLeave);
    raf = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseleave", onLeave);
    };
  }, []);

  return (
    <div aria-hidden className="cursor-trail pointer-events-none fixed inset-0 z-[100]">
      {Array.from({ length: COUNT }).map((_, i) => (
        <div
          key={i}
          ref={(el) => {
            nodesRef.current[i] = el;
          }}
          className="absolute left-0 top-0 bg-cobalt"
          style={{ willChange: "transform, opacity" }}
        />
      ))}
    </div>
  );
}
