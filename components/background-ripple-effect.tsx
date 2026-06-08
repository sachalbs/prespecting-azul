"use client";

// Faithful port of the Framer "BackgroundRippleEffect" code component.
// The only changes vs. the original are the Framer-editor-only imports
// (addPropertyControls / ControlType / useIsStaticRenderer), which are stubbed
// out. The runtime logic and framer-motion usage are identical.

import {
  useMemo,
  useRef,
  useState,
  useEffect,
  startTransition,
  useCallback,
  type CSSProperties,
} from "react";
import { motion, useInView } from "framer-motion";

const useIsStaticRenderer = () => false;

type Shape = "square" | "circle" | "triangle" | "hexagon" | "diamond";

type Props = {
  rows?: number;
  cols?: number;
  cellSize?: number;
  borderColor?: string;
  fillColor?: string;
  shadowColor?: string;
  opacity?: number;
  hoverOpacity?: number;
  animationDuration?: number;
  animationDelay?: number;
  showShadow?: boolean;
  interactive?: boolean;
  shapeType?: Shape;
  style?: CSSProperties;
};

export default function BackgroundRippleEffect(props: Props) {
  const {
    rows = 8,
    cols = 27,
    cellSize = 56,
    borderColor = "#E5E5E5",
    fillColor = "#F5F5F5",
    shadowColor = "#CCCCCC",
    opacity = 40,
    hoverOpacity = 80,
    animationDuration = 200,
    animationDelay = 55,
    showShadow = true,
    interactive = true,
    shapeType = "square",
  } = props;

  const [clickedCell, setClickedCell] = useState<{ row: number; col: number } | null>(null);
  const [rippleKey, setRippleKey] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const isStatic = useIsStaticRenderer();
  const isInView = useInView(containerRef, { once: false, margin: "100px" });

  // Fill the whole container: derive the grid size from the measured box so the
  // background spans the full width/height on any viewport (the original is a
  // fixed-size centred grid, which left empty bands on the sides).
  const [auto, setAuto] = useState<{ rows: number; cols: number } | null>(null);
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const measure = () => {
      const r = el.getBoundingClientRect();
      setAuto({
        cols: Math.ceil(r.width / cellSize) + 1,
        rows: Math.ceil(r.height / cellSize) + 1,
      });
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [cellSize]);

  const effRows = auto?.rows ?? rows;
  const effCols = auto?.cols ?? cols;

  // Optimize for large grids by limiting cell count
  const maxCells = 1e3;
  const totalCells = effRows * effCols;
  const shouldVirtualize = totalCells > maxCells;
  const actualRows = shouldVirtualize ? Math.min(effRows, Math.floor(maxCells / effCols)) : effRows;
  const actualCols = shouldVirtualize ? Math.min(effCols, Math.floor(maxCells / effRows)) : effCols;

  const cells = useMemo(
    () => Array.from({ length: actualRows * actualCols }, (_, idx) => idx),
    [actualRows, actualCols],
  );

  const gridStyle: CSSProperties = {
    display: "grid",
    gridTemplateColumns: `repeat(${actualCols}, ${cellSize}px)`,
    gridTemplateRows: `repeat(${actualRows}, ${cellSize}px)`,
    width: actualCols * cellSize,
    height: actualRows * cellSize,
    margin: "0 auto",
    willChange: "transform",
    transform: "translate3d(0, 0, 0)",
  };

  const handleCellClick = useCallback(
    (rowIdx: number, colIdx: number) => {
      if (!interactive || isStatic) return;
      startTransition(() => {
        setClickedCell({ row: rowIdx, col: colIdx });
        setRippleKey((k) => k + 1);
      });
    },
    [interactive, isStatic],
  );

  // Don't animate if not in view or static renderer
  const shouldAnimate = isInView && !isStatic;

  const getShapeStyles = useCallback(
    (shape: string): CSSProperties => {
      const baseSize = cellSize - 2; // Account for border
      switch (shape) {
        case "circle":
          return { borderRadius: "50%", width: baseSize, height: baseSize };
        case "triangle":
          return {
            width: 0,
            height: 0,
            backgroundColor: "transparent",
            borderLeft: `${baseSize / 2}px solid transparent`,
            borderRight: `${baseSize / 2}px solid transparent`,
            borderBottom: `${baseSize}px solid ${fillColor}`,
            border: "none",
          };
        case "hexagon":
          return {
            width: baseSize,
            height: baseSize * 0.866,
            clipPath: "polygon(30% 0%, 70% 0%, 100% 50%, 70% 100%, 30% 100%, 0% 50%)",
          };
        case "diamond":
          return { width: baseSize, height: baseSize, transform: "rotate(45deg)", transformOrigin: "center" };
        default:
          return { width: baseSize, height: baseSize };
      }
    },
    [cellSize, fillColor],
  );

  return (
    <div
      ref={containerRef}
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        overflow: "hidden",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        ...props.style,
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          zIndex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div style={{ position: "relative", zIndex: 3, ...gridStyle }}>
          {cells.map((idx) => {
            const rowIdx = Math.floor(idx / actualCols);
            const colIdx = idx % actualCols;
            const distance = clickedCell
              ? Math.hypot(clickedCell.row - rowIdx, clickedCell.col - colIdx)
              : 0;
            const delay = clickedCell ? Math.max(0, distance * animationDelay) : 0;
            const duration = animationDuration + distance * 80;
            return (
              <motion.div
                key={`${idx}-${rippleKey}`}
                style={{
                  position: "relative",
                  backgroundColor: shapeType === "triangle" ? "transparent" : fillColor,
                  border: shapeType === "triangle" ? "none" : `0.5px solid ${borderColor}`,
                  opacity: opacity / 100,
                  cursor: interactive ? "pointer" : "default",
                  pointerEvents: interactive ? "auto" : "none",
                  willChange: shouldAnimate ? "transform, opacity" : "auto",
                  transform: "translate3d(0, 0, 0)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  ...getShapeStyles(shapeType),
                  ...(showShadow &&
                    shapeType !== "triangle" && {
                      boxShadow: `0px 0px 40px 1px ${shadowColor} inset`,
                    }),
                }}
                onClick={() => handleCellClick(rowIdx, colIdx)}
                whileHover={
                  interactive && shouldAnimate
                    ? { opacity: hoverOpacity / 100, transition: { duration: 0.15 } }
                    : {}
                }
                animate={
                  clickedCell && shouldAnimate
                    ? { scale: [1, 1.1, 1], opacity: [opacity / 100, 1, opacity / 100] }
                    : {}
                }
                transition={
                  clickedCell && shouldAnimate
                    ? { delay: delay / 1000, duration: Math.min(duration / 1000, 2), ease: "easeOut" }
                    : {}
                }
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}
