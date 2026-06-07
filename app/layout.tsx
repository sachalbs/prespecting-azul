import type { Metadata, Viewport } from "next";
import { Archivo, Inter } from "next/font/google";
import "./globals.css";

const display = Archivo({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

const sans = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const title = "Azul — Le commercial autonome qui fait répondre vos prospects";
const description =
  "Azul est un commercial autonome (SDR) propulsé par l'IA. Il recherche chaque prospect en profondeur, écrit un message vraiment personnel, et fait grimper votre taux de réponse. Vous le pilotez depuis Slack, WhatsApp ou Teams.";

export const metadata: Metadata = {
  title,
  description,
  applicationName: "Azul",
  openGraph: {
    title,
    description,
    siteName: "Azul",
    locale: "fr_FR",
    type: "website",
  },
  twitter: { card: "summary_large_image", title, description },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#F1EFE9",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr" className={`${display.variable} ${sans.variable}`}>
      <body className="min-h-dvh">{children}</body>
    </html>
  );
}
