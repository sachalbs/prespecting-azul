import type { Metadata } from "next";
import { LangProvider } from "@/components/lang-provider";
import { ConnectHeader } from "@/components/connect-header";
import { ConnectChannels } from "@/components/connect-channels";

export const metadata: Metadata = {
  title: "Choose your channel · Azul",
  description:
    "Pick where you want to talk to Azul: WhatsApp, Slack or Teams. One decision, zero setup.",
  robots: { index: false, follow: false },
};

export default function ConnectPage() {
  return (
    <LangProvider>
      <ConnectHeader />
      <main className="flex min-h-[calc(100dvh-4rem)] flex-col">
        <ConnectChannels />
      </main>
    </LangProvider>
  );
}
