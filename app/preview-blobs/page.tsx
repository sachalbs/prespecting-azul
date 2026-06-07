// Temporary gallery to compare the floating-shape options live.
// Visit /preview-blobs on the deployed preview to see them animate.

const VIDEO_SRC =
  "https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260518_003132_8b7edcb6-c64d-4a52-a9ca-879942e122ad.mp4";

function Tile({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="text-center">
      <div className="relative mx-auto aspect-square w-full max-w-[260px]">{children}</div>
      <p className="mt-6 font-mono text-[0.7rem] uppercase tracking-[0.18em] text-ink">
        {label}
      </p>
    </div>
  );
}

function Blob({ cls }: { cls?: string }) {
  return (
    <>
      <div aria-hidden className="absolute inset-8 rounded-full bg-cobalt/20 blur-3xl" />
      <div aria-hidden className={`liquid-blob absolute inset-0 ${cls ?? ""}`} />
    </>
  );
}

export default function PreviewBlobs() {
  return (
    <div className="min-h-dvh bg-paper px-10 py-16">
      <p className="mx-auto mb-12 max-w-6xl font-mono text-[0.72rem] uppercase tracking-[0.18em] text-muted">
        Azul · formes flottantes — choisis ta version
      </p>
      <div className="mx-auto grid max-w-6xl grid-cols-2 gap-12 lg:grid-cols-4">
        <Tile label="A — Bleu glossy">
          <Blob />
        </Tile>
        <Tile label="B — Aluminium chromé">
          <Blob cls="is-metal" />
        </Tile>
        <Tile label="C — Bleu chromé">
          <Blob cls="is-bluechrome" />
        </Tile>
        <Tile label="D — Ta vidéo (live)">
          <video
            className="h-full w-full rounded-[1.6rem] object-cover"
            autoPlay
            muted
            loop
            playsInline
            preload="auto"
            aria-hidden
          >
            <source src={VIDEO_SRC} type="video/mp4" />
          </video>
        </Tile>
      </div>
    </div>
  );
}
