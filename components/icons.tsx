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
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden {...props}>
      <path d="M6 14.5a2 2 0 1 1-2-2h2v2Zm1 0a2 2 0 1 1 4 0v5a2 2 0 1 1-4 0v-5Z" />
      <path d="M9.5 6a2 2 0 1 1 2-2v2h-2Zm0 1a2 2 0 1 1 0 4h-5a2 2 0 1 1 0-4h5Z" />
      <path d="M18 9.5a2 2 0 1 1 2 2h-2v-2Zm-1 0a2 2 0 1 1-4 0v-5a2 2 0 1 1 4 0v5Z" />
      <path d="M14.5 18a2 2 0 1 1-2 2v-2h2Zm0-1a2 2 0 1 1 0-4h5a2 2 0 1 1 0 4h-5Z" />
    </svg>
  );
}

export function WhatsAppMark(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden {...props}>
      <path d="M12 2.4a9.5 9.5 0 0 0-8.1 14.4L2.4 21.6l4.9-1.4A9.5 9.5 0 1 0 12 2.4Zm0 1.8a7.7 7.7 0 0 1 6.5 11.8c-.2.3-.2.3-.4 1l.7 2.4-2.4-.7c-.5.1-.6.2-1 .3A7.7 7.7 0 1 1 12 4.2Zm-3 3.3c-.2 0-.5.1-.7.4-.3.3-.9.9-.9 2.1s.9 2.4 1 2.6c.1.2 1.8 2.9 4.5 3.9 2.2.9 2.6.7 3.1.7.5 0 1.5-.6 1.7-1.2.2-.6.2-1.1.2-1.2-.1-.1-.3-.2-.6-.4l-1.6-.8c-.2-.1-.4-.1-.6.1l-.7.9c-.1.2-.3.2-.5.1-.3-.1-1.2-.4-2.2-1.4-.8-.7-1.3-1.6-1.5-1.9-.1-.2 0-.4.1-.5l.4-.5c.1-.2.2-.3.3-.5.1-.2 0-.4 0-.5l-.8-1.9c-.2-.4-.4-.4-.6-.4Z" />
    </svg>
  );
}

export function TeamsMark(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden {...props}>
      <path d="M3.5 7.5h8.2v2H8.9v7h-2.4v-7H3.5v-2Z" />
      <path d="M14.6 7.2a2 2 0 1 0 0-.1ZM13 11h7a1 1 0 0 1 1 1v3.6a3.6 3.6 0 0 1-3.6 3.6H16a3 3 0 0 1-3-3v-5.2Z" />
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
    <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden {...props}>
      <path d="M4.5 3.5a2 2 0 1 0 0 4 2 2 0 0 0 0-4ZM3 9h3v12H3V9Zm5.5 0H11v1.7h.1c.4-.7 1.4-1.7 3.1-1.7 3.3 0 3.9 2.1 3.9 4.9V21h-3v-5.4c0-1.3 0-3-1.9-3s-2.1 1.4-2.1 2.9V21h-3V9Z" />
    </svg>
  );
}
