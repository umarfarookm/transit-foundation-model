import Script from "next/script";
import { GA_ID, analyticsSnippet } from "@/lib/analytics";

/** Loads Google Analytics after the page is interactive. See src/lib/analytics.ts. */
export function Analytics() {
  return (
    <Script id="ga4" strategy="afterInteractive">
      {analyticsSnippet(GA_ID)}
    </Script>
  );
}
