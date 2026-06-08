"use client";

import { useId, useState, type FormEvent } from "react";
import { WideArrow, Check } from "./icons";
import { useLang } from "./lang-provider";

type Status = "idle" | "loading" | "success" | "error";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function WaitlistForm() {
  const { t } = useLang();
  const f = t.form;
  const id = useId();
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (status === "loading") return;

    if (!EMAIL_RE.test(email.trim())) {
      setStatus("error");
      setError(f.errEmail);
      return;
    }

    setStatus("loading");
    setError(null);

    try {
      const res = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });
      if (!res.ok) throw new Error("request failed");
      setStatus("success");
    } catch {
      setStatus("error");
      setError(f.errGeneric);
    }
  }

  if (status === "success") {
    return (
      <div
        role="status"
        className="flex items-start gap-3 border border-ink bg-panel px-5 py-4 text-[0.95rem]"
      >
        <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center bg-cobalt text-white">
          <Check className="h-3.5 w-3.5" />
        </span>
        <p className="leading-relaxed text-ink">
          <span className="font-semibold">{f.successTitle}</span>{" "}
          <span className="text-muted">{f.successBody}</span>
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} noValidate className="w-full">
      <label htmlFor={id} className="label mb-2 block">
        <span className="sq" /> {f.label}
      </label>
      <div className="flex flex-col gap-2.5 sm:flex-row">
        <input
          id={id}
          type="email"
          name="email"
          inputMode="email"
          autoComplete="email"
          required
          placeholder={f.placeholder}
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (status === "error") {
              setStatus("idle");
              setError(null);
            }
          }}
          aria-invalid={status === "error"}
          aria-describedby={error ? `${id}-err` : undefined}
          className={`field flex-1 ${status === "error" ? "!border-red-500" : ""}`}
        />
        <button
          type="submit"
          disabled={status === "loading"}
          className="btn h-[3.25rem] whitespace-nowrap"
        >
          {status === "loading" ? f.loading : f.submit}
          {status !== "loading" && <WideArrow className="h-3 w-7" />}
        </button>
      </div>

      <p
        id={`${id}-err`}
        aria-live="polite"
        className={`min-h-[1.2rem] pt-2 text-[0.83rem] font-medium ${
          status === "error" ? "text-red-600" : "text-transparent"
        }`}
      >
        {error ?? "placeholder"}
      </p>
    </form>
  );
}
