import type { Metadata, Viewport } from "next";
import { Archivo, Inter, JetBrains_Mono } from "next/font/google";
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

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

const title = "Azul: The autonomous rep that gets your prospects to reply";
const description =
  "Azul is an autonomous AI sales rep (SDR). It researches every prospect in depth, writes a genuinely personal message, and drives up your reply rate. You manage it from Slack, WhatsApp or Teams.";

export const metadata: Metadata = {
  title,
  description,
  applicationName: "Azul",
  openGraph: {
    title,
    description,
    siteName: "Azul",
    locale: "en_US",
    alternateLocale: "fr_FR",
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
    <html
      lang="en"
      className={`${display.variable} ${sans.variable} ${mono.variable}`}
    >
      <body className="min-h-dvh">{children}</body>
    </html>
  );
}
