import { NextResponse } from "next/server";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

/**
 * Waitlist endpoint.
 *
 * For now this validates the submission and acknowledges it. Wiring it to a
 * real store is a one-function change — drop the integration where indicated
 * below (e.g. a Notion database, Resend audience, Google Sheet, or a DB).
 * Nothing here invents data or sends anything on the user's behalf yet.
 */
export async function POST(request: Request) {
  let payload: unknown;
  try {
    payload = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid request body." }, { status: 400 });
  }

  const email =
    typeof payload === "object" && payload !== null && "email" in payload
      ? String((payload as { email: unknown }).email ?? "").trim()
      : "";

  if (!EMAIL_RE.test(email)) {
    return NextResponse.json({ error: "Invalid email address." }, { status: 400 });
  }

  // --- Persist the signup here -------------------------------------------
  // e.g. await addToNotionWaitlist(email)  /  await resend.contacts.create(...)
  // Until that is wired, we log so early signups are not silently lost.
  console.info("[waitlist] signup", { email, at: new Date().toISOString() });
  // -----------------------------------------------------------------------

  return NextResponse.json({ ok: true });
}
