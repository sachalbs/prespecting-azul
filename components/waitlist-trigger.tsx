"use client";

import type { CSSProperties, ReactNode } from "react";
import { PopupButton } from "@typeform/embed-react";

// The waitlist lives in Typeform. Every "Join the waitlist" CTA opens it as a
// popup overlay so the visitor never leaves the page.
export const TYPEFORM_ID = "P0LQgp8A";

export function WaitlistTrigger({
  className,
  children,
  style,
  ariaLabel,
}: {
  className?: string;
  children: ReactNode;
  style?: CSSProperties;
  ariaLabel?: string;
}) {
  return (
    <PopupButton
      id={TYPEFORM_ID}
      size={80}
      className={className}
      style={style}
      buttonProps={ariaLabel ? { "aria-label": ariaLabel } : undefined}
    >
      {children}
    </PopupButton>
  );
}
