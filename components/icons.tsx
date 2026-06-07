import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

/* ---- UI icons (outline, consistent 1.7 stroke) ------------------------- */

const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.7,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
};

export function ArrowRight(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M4 12h15" />
      <path d="m13 6 6 6-6 6" />
    </svg>
  );
}

export function WideArrow(props: IconProps) {
  return (
    <svg
      viewBox="0 0 30 12"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      {...props}
    >
      <path d="M1 6h27" />
      <path d="m23 1.5 5 4.5-5 4.5" />
    </svg>
  );
}

export function Check(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="m4.5 12.5 4.5 4.5 10.5-11" />
    </svg>
  );
}

export function Search(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m20 20-3.6-3.6" />
    </svg>
  );
}

export function Pen(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M14.5 5.5 18.5 9.5" />
      <path d="M5 19l1-4L16 5a2.1 2.1 0 0 1 3 3L9 18l-4 1Z" />
    </svg>
  );
}

export function Loop(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M4 11a8 8 0 0 1 14-5l2 2" />
      <path d="M20 5v4h-4" />
      <path d="M20 13a8 8 0 0 1-14 5l-2-2" />
      <path d="M4 19v-4h4" />
    </svg>
  );
}

export function Reply(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M9 7 4 12l5 5" />
      <path d="M4 12h9a7 7 0 0 1 7 7v1" />
    </svg>
  );
}

export function Spark(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6.3 6.3l2.4 2.4M15.3 15.3l2.4 2.4M17.7 6.3l-2.4 2.4M8.7 15.3l-2.4 2.4" />
    </svg>
  );
}

export function Minus(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M5 12h14" />
    </svg>
  );
}

export function Cross(props: IconProps) {
  return (
    <svg {...base} {...props}>
      <path d="M6 6l12 12M18 6 6 18" />
    </svg>
  );
}

/* ---- Channel marks (monochrome, schematic — inherit currentColor) ------ */
/* Kept single-color and simplified on purpose: these signal "works with",
   they are not reproductions of the official multi-color brand logos.      */

export function SlackMark(props: IconProps) {
  return (
    <svg viewBox="0 0 122.8 122.8" aria-hidden {...props}>
      <path d="M25.8 77.6a12.9 12.9 0 1 1-12.9-12.9h12.9v12.9z" fill="#E01E5A" />
      <path d="M32.3 77.6a12.9 12.9 0 0 1 25.8 0v32.3a12.9 12.9 0 0 1-25.8 0V77.6z" fill="#E01E5A" />
      <path d="M45.2 25.8a12.9 12.9 0 1 1 12.9-12.9v12.9H45.2z" fill="#36C5F0" />
      <path d="M45.2 32.3a12.9 12.9 0 0 1 0 25.8H12.9a12.9 12.9 0 0 1 0-25.8h32.3z" fill="#36C5F0" />
      <path d="M97 45.2a12.9 12.9 0 1 1 12.9 12.9H97V45.2z" fill="#2EB67D" />
      <path d="M90.5 45.2a12.9 12.9 0 0 1-25.8 0V12.9a12.9 12.9 0 0 1 25.8 0v32.3z" fill="#2EB67D" />
      <path d="M77.6 97a12.9 12.9 0 1 1-12.9 12.9V97h12.9z" fill="#ECB22E" />
      <path d="M77.6 90.5a12.9 12.9 0 0 1 0-25.8h32.3a12.9 12.9 0 0 1 0 25.8H77.6z" fill="#ECB22E" />
    </svg>
  );
}

export function WhatsAppMark(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden {...props}>
      <path d="M12.04 2.5a9.46 9.46 0 0 0-8.1 14.3L2.5 21.5l4.84-1.42A9.46 9.46 0 1 0 12.04 2.5Zm0 1.73a7.72 7.72 0 1 1-3.93 14.37l-.28-.17-2.87.84.85-2.8-.18-.29A7.72 7.72 0 0 1 12.04 4.23ZM8.5 7.9c-.17 0-.44.06-.67.31-.23.25-.88.86-.88 2.1 0 1.23.9 2.42 1.03 2.59.13.17 1.77 2.84 4.37 3.86 2.16.85 2.6.68 3.07.64.47-.04 1.5-.61 1.72-1.2.21-.59.21-1.1.15-1.2-.06-.1-.23-.17-.48-.3-.25-.12-1.5-.74-1.73-.82-.23-.08-.4-.13-.56.13-.17.25-.64.82-.79.99-.14.17-.29.19-.54.06-.25-.13-1.06-.39-2.02-1.25-.75-.66-1.25-1.48-1.4-1.73-.14-.25-.01-.39.11-.51.11-.11.25-.29.38-.43.12-.15.16-.25.25-.42.08-.17.04-.31-.02-.44-.06-.12-.56-1.37-.78-1.87-.2-.48-.41-.42-.56-.42H8.5Z" />
    </svg>
  );
}

export function TeamsMark(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden {...props}>
      <path
        fillRule="evenodd"
        clipRule="evenodd"
        d="M4.6 4.5h14.8a1.8 1.8 0 0 1 1.8 1.8v11.4a1.8 1.8 0 0 1-1.8 1.8H4.6a1.8 1.8 0 0 1-1.8-1.8V6.3a1.8 1.8 0 0 1 1.8-1.8ZM7.5 9.1v1.9h2.6v6.4h2.2v-6.4h2.6V9.1H7.5Z"
      />
    </svg>
  );
}

export function MailMark(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden {...props}>
      <rect x="3" y="5.5" width="18" height="13" rx="2.5" />
      <path d="m4 7 8 5.5L20 7" />
    </svg>
  );
}

export function LinkedInMark(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden {...props}>
      <rect width="24" height="24" rx="4" fill="#0A66C2" />
      <path
        fill="#fff"
        d="M8.34 18.5H5.4V9.6h2.94v8.9ZM6.87 8.34a1.71 1.71 0 1 1 0-3.42 1.71 1.71 0 0 1 0 3.42ZM18.6 18.5h-2.93v-4.33c0-1.03-.02-2.36-1.44-2.36-1.44 0-1.66 1.13-1.66 2.29v4.4h-2.93V9.6h2.81v1.22h.04c.39-.74 1.35-1.52 2.78-1.52 2.97 0 3.52 1.96 3.52 4.5v4.7Z"
      />
    </svg>
  );
}
