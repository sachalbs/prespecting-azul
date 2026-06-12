# Design

ELYS-style Swiss / brutalist instrument. Warm paper canvas, near-black ink, a
single cobalt accent. Hard edges, hairline rules, heavy uppercase display type.
The page should read like a precision tool, not a marketing site.

## Color

Light theme only (`color-scheme: light`). Restrained strategy: tinted neutral
canvas + one saturated accent held under ~10% of the surface.

| Token | Value | Role |
|---|---|---|
| `paper` | `#F1EFE9` | Page canvas (warm paper) |
| `panel` | `#FBFAF6` | Raised surfaces (cards, waitlist panel) |
| `ink` | `#111114` | Primary text, borders, hard shadow |
| `muted` | `#56585F` | Secondary text (≈6.8:1 on paper — AA) |
| `line` | `#D8D6CD` | Hairline rules, dividers |
| `cobalt.600` | `#2C4EE6` | The accent: CTAs, highlights, one word per heading |
| `cobalt.500/700` | `#3C58EA` / `#2240C4` | Hover / active on cobalt |

Accent discipline: cobalt appears as the button fill, one highlighted word per
section heading, the `■` wordmark tile, reference highlights in the demo message,
and the step-diagram accents. Never two competing accents.

## Typography

Three families, contrast-paired (heavy grotesque display + neutral humanist body
+ technical mono labels):

- **Display** — Archivo (Black/900, uppercase, `tracking-[-0.02em]`, `leading-[0.92]`).
  Headlines and the big step numbers.
- **Body** — Inter. Paragraphs, card copy.
- **Mono** — JetBrains Mono. Eyebrows/labels and system microcopy only (`.label`,
  `tracking-label` 0.18em, uppercase, ≤4 words).

Heading scale uses fluid `clamp()`; hero max ~4.4rem. One cobalt word per heading
for emphasis.

## Components

- **`.btn`** — brutalist primary. `border-2 border-ink bg-cobalt`, white uppercase
  bold, hard offset shadow `5px 5px 0 0 ink`; hover lifts to 7px + cobalt.500,
  active presses to 2px. The only primary button style.
- **`.label`** — mono uppercase eyebrow with a leading cobalt index.
- **Message card** — `border-2 border-ink bg-panel` with a `6px 6px` cobalt hard
  shadow; renders a real researched outbound message with cobalt reference
  highlights and a "Draft · to approve" footer (human-in-the-loop proof).
- **Step tiles** — 64px blueprint-grid framed tiles with monochrome+cobalt SVG
  diagrams (radar / draft / broadcast).
- **Wordmark** — "AZUL" (Archivo black) + a cobalt `■` square.

## Layout

- Container: `max-w-content` (82rem), fluid `shell` padding (`px-5 → px-12`).
- Hero is full-viewport (`min-h-[calc(100dvh-4rem)]`) with a click-rippling grid
  behind the content (z-0) and the WebGL liquid-metal blob as the focal object.
- Hairline `border-line` rules separate hero bands; sections use generous fluid
  vertical rhythm (`py-20 → py-28`).

## Motion

Intentional, ease-out, reduced-motion-safe.

- On-load: clip-reveal headline rise + staggered `.enter` fades (hero only).
- Scroll: subtle fade-up `.reveal` (content visible by default; the class only
  enhances).
- Ambient: the liquid-metal blob (WebGL, Float + distort) and a discreet cobalt
  cursor-trail comet (desktop, hover-capable only).
- Interaction: brutalist button lift/press; ripple grid on click.
- Every effect has a `prefers-reduced-motion: reduce` off-switch.
