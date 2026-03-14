import { Analytics } from "@vercel/analytics/next";
import { SpeedInsights } from "@vercel/speed-insights/next";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

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
  url: "https://exploreion.org",
  applicationCategory: "EducationalApplication",
  operatingSystem: "Web",
  description:
    "Explorion transforms technical content into interactive visual explanations with AI-generated Manim animations.",
  author: [
    {
      "@type": "Person",
      name: "Vardan Agarwal",
    },
    {
      "@type": "Person",
      name: "Jatin Tilwani",
    },
  ],
  offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
  keywords:
    "Explorion, research paper visualizer, Manim, scrollytelling, AI, machine learning",
};

export const metadata: Metadata = {
  metadataBase: new URL("https://exploreion.org"),
  title: {
    default: "Explorion — Technical Content, Visualized",
    template: "%s · Explorion",
  },
  description:
    "Explorion transforms any research paper or technical document into an interactive scrollytelling experience with AI-generated Manim animations.",
  applicationName: "Explorion",
  keywords: [
    "Explorion",
    "Explorion AI",
    "research paper visualizer",
    "research paper explainer",
    "Manim animations",
    "AI paper summary",
    "scrollytelling",
    "machine learning visualization",
    "academic paper visualization",
    "computer science",
    "AI research",
    "paper to video",
    "Vardan Agarwal",
    "Jatin Tilwani",
  ],
  authors: [
    { name: "Vardan Agarwal" },
    { name: "Jatin Tilwani" },
  ],
  creator: "Vardan Agarwal, Jatin Tilwani",
  openGraph: {
    type: "website",
    url: "https://exploreion.org",
    siteName: "Explorion",
    title: "Explorion — Technical Content, Visualized",
    description:
      "Transform any research paper into an interactive scrollytelling experience with AI-generated Manim animations.",
    images: [
      {
        url: "/landing.jpeg",
        width: 1200,
        height: 630,
        alt: "Explorion — papers transformed into animated visual explanations",
      },
    ],
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "Explorion — Technical Content, Visualized",
    description:
      "Transform any research paper into an interactive scrollytelling experience with AI-generated Manim animations.",
    images: ["/landing.jpeg"],
  },
  icons: {
    icon: [
      { url: "/logo-new.png", type: "image/png" },
      { url: "/logo-new.png", sizes: "any" },
    ],
    apple: [{ url: "/logo-new.png", type: "image/png" }],
  },
  alternates: {
    canonical: "https://exploreion.org",
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
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
        <div className="min-h-dvh">{children}</div>
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
