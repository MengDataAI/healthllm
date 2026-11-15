import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";
import Footer from "@/components/Footer";

export const metadata: Metadata = {
  title: "HealthLLM — Open Health AI Hub",
  description: "Browse 329 health LLMs, 266 datasets, run reproducible evals, and contribute your model in one pull request.",
  openGraph: {
    title: "HealthLLM — Open Health AI Hub",
    description: "The open hub for health AI — models, datasets, and reproducible benchmarks.",
    url: "https://healthxllm.netlify.app",
    siteName: "HealthLLM",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <a className="skip" href="#main">Skip to content</a>
        <Header />
        <main id="main">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
