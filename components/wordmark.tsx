/** Wordmark lockup: "AZUL" + a cobalt square, in the ELYS spirit. */
export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-end gap-[0.34rem] ${className}`}>
      <span className="font-display text-[1.7rem] font-black uppercase leading-none tracking-[-0.01em] text-ink">
        Azul
      </span>
      <span className="mb-[0.22em] h-[0.55rem] w-[0.55rem] bg-cobalt" aria-hidden />
    </span>
  );
}

/** Square cobalt tile with a white "A", used as Azul's avatar in the chat. */
export function AzulTile({ className = "" }: { className?: string }) {
  return (
    <span
      aria-hidden
      className={`inline-flex items-center justify-center bg-cobalt font-display font-black uppercase leading-none text-white ${className}`}
    >
      A
    </span>
  );
}
