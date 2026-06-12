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

/* ---- Channel marks (monochrome, schematic, inherit currentColor) ------ */
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
    <svg viewBox="0 0 24 24" aria-hidden {...props}>
      <path
        fill="#25D366"
        d="M.06 24l1.68-6.13A11.83 11.83 0 0 1 .14 11.9C.14 5.33 5.49 0 12.06 0c3.18 0 6.17 1.24 8.42 3.49a11.76 11.76 0 0 1 3.48 8.42c0 6.56-5.35 11.9-11.92 11.9h-.01a11.9 11.9 0 0 1-5.69-1.45L.06 24Z"
      />
      <path
        fill="#fff"
        d="M9.1 6.9c-.18-.4-.36-.41-.53-.42l-.45-.01c-.16 0-.41.06-.63.3-.22.24-.83.81-.83 1.97 0 1.16.85 2.29.97 2.45.12.16 1.65 2.64 4.08 3.7.58.26 1.04.41 1.39.52.58.19 1.11.16 1.53.1.47-.07 1.44-.59 1.64-1.16.2-.57.2-1.06.14-1.16-.06-.1-.22-.16-.46-.28-.24-.12-1.44-.71-1.66-.79-.22-.08-.39-.12-.55.12-.16.24-.63.79-.78.95-.14.16-.29.18-.53.06-.24-.12-1.02-.38-1.95-1.2-.72-.64-1.21-1.44-1.35-1.68-.14-.24-.02-.37.1-.49.11-.11.24-.29.37-.43.12-.14.16-.24.24-.4.08-.16.04-.3-.02-.42-.06-.12-.54-1.33-.76-1.81Z"
      />
    </svg>
  );
}

export function TeamsMark(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden {...props}>
      <circle cx="17.1" cy="6.3" r="2.5" fill="#7B83EB" />
      <path
        fill="#7B83EB"
        d="M21.5 10.3h-6.2v5.2a3.1 3.1 0 1 0 6.2 0v-4.5a.7.7 0 0 0-.7-.7Z"
      />
      <rect x="2.5" y="5.6" width="11.7" height="12.8" rx="1.8" fill="#5059C9" />
      <path fill="#fff" d="M4.9 8.2h6.9v1.7H9.3v6.1H7.4V9.9H4.9V8.2Z" />
    </svg>
  );
}

export function TelegramMark(props: IconProps) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden {...props}>
      <circle cx="12" cy="12" r="12" fill="#26A5E4" />
      <path
        fill="#fff"
        d="M5.4 11.7c3.5-1.5 5.8-2.5 7-3 3.3-1.4 4-1.6 4.5-1.6.1 0 .3 0 .5.2.1.1.2.3.2.4v.6c-.2 1.9-1 6.5-1.4 8.6-.2.9-.5 1.2-.9 1.2-.7.1-1.3-.5-2-1-1.1-.7-1.8-1.2-2.8-1.9-1.2-.8-.4-1.3.3-2 .2-.2 3.3-3 3.4-3.3 0 0 0-.2-.1-.2-.1-.1-.2 0-.3 0l-5.5 3.5c-.5.4-1 .5-1.4.5-.5 0-1.4-.2-2-.4-.8-.3-1.5-.4-1.4-.9 0-.2.3-.4.9-.7Z"
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
