import { SiteHeader } from "@/components/site-header";
import { Hero } from "@/components/hero";
import { Problem } from "@/components/problem";
import { Pilot } from "@/components/pilot";
import { HowItWorks } from "@/components/how-it-works";
import { Metric } from "@/components/metric";
import { Waitlist } from "@/components/waitlist";
import { SiteFooter } from "@/components/site-footer";

export default function Home() {
  return (
    <>
      <SiteHeader />
      <main>
        <Hero />
        <Problem />
        <Pilot />
        <HowItWorks />
        <Metric />
        <Waitlist />
      </main>
      <SiteFooter />
    </>
  );
}
