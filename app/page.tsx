import { LangProvider } from "@/components/lang-provider";
import { SiteHeader } from "@/components/site-header";
import { Hero } from "@/components/hero";
import { Problem } from "@/components/problem";
import { HowItWorks } from "@/components/how-it-works";
import { Waitlist } from "@/components/waitlist";
import { SiteFooter } from "@/components/site-footer";
import CursorTrail from "@/components/cursor-trail";

export default function Home() {
  return (
    <LangProvider>
      <CursorTrail />
      <SiteHeader />
      <main>
        <Hero />
        <Problem />
        <HowItWorks />
        <Waitlist />
      </main>
      <SiteFooter />
    </LangProvider>
  );
}
