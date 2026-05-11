import { Analytics } from "@vercel/analytics/next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import "@solana/wallet-adapter-react-ui/styles.css";
import { SolanaProvider } from "@/components/SolanaProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "Explorion",
  alternateName: [
    "explorion",
    "explorion ai",
    "explorion visuals",
  ],
  url: "https://explorion.ai",
  applicationCategory: "EducationalApplication",
  operatingSystem: "Web",
  description:
    "Explorion transforms complex technical strategies and research papers into interactive cinematic explainers with AI-generated visualizations.",
};

export const metadata: Metadata = {
  metadataBase: new URL("https://explorion.tech"),
  title: {
    default: "Explorion — Decode the Complex",
    template: "%s · Explorion",
  },
  description:
    "Explorion transforms any technical paper, strategy, or repo into an interactive cinematic explainer with AI-generated Manim animations. Paste a URL or strategy and watch concepts come to life.",
  applicationName: "Explorion",
  keywords: [
    "Explorion",
    "explorion ai",
    "technical explainer",
    "research paper visualizer",
    "Manim animations",
    "AI paper summary",
    "cinematic explanations",
    "scrollytelling",
    "machine learning visualization",
    "Solana",
    "web3 strategy",
  ],
  openGraph: {
    type: "website",
    url: "https://explorion.ai",
    siteName: "Explorion",
    title: "Explorion — Decode the Complex",
    description:
      "Transform any technical content into an interactive cinematic explainer with AI-generated Manim animations.",
    images: [
      {
        url: "/logo.png",
        width: 1200,
        height: 630,
        alt: "Explorion — Cinematic Visual Explanations",
      },
    ],
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "Explorion — Decode the Complex",
    description:
      "Transform any technical content into an interactive cinematic explainer with AI-generated Manim animations.",
    images: ["/logo.png"],
  },
  icons: {
    icon: [
      { url: "/logo.png", type: "image/png" },
      { url: "/logo.png", sizes: "any" },
    ],
    apple: [{ url: "/logo.png", type: "image/png" }],
  },
  alternates: {
    canonical: "https://explorion.ai",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-dvh bg-black text-[#e8e8e8]`}
      >
        <SolanaProvider>
          <div className="min-h-dvh">{children}</div>
        </SolanaProvider>
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
