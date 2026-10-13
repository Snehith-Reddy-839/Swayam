import type { Metadata } from "next";
import { Suspense } from "react";
import "./globals.css";
import { Navbar } from "@/components/Navbar";
import { BottomNav } from "@/components/BottomNav";

export const metadata: Metadata = {
  title: "MunchMate — Group Ordering Made Effortless",
  description:
    "The modern collaborative late-night food & grocery ordering app for hostelers, roommates, and college groups. Shared carts, precise bill splitting, and instant UPI payments.",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full antialiased">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Outfit:wght@400;500;600;700;800;900&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="min-h-full flex flex-col bg-[#FAF8F5] text-[#1A1A1A] pb-16 md:pb-0 font-['Plus_Jakarta_Sans',sans-serif]">
        <Suspense fallback={<div className="h-16 bg-white border-b border-[#EFE8DE]" />}>
          <Navbar />
        </Suspense>
        <main className="flex-1">
          <Suspense fallback={<div className="max-w-4xl mx-auto py-12 text-center text-xs text-[#71717A]">Loading MunchMate...</div>}>
            {children}
          </Suspense>
        </main>
        <Suspense fallback={null}>
          <BottomNav />
        </Suspense>
      </body>
    </html>
  );
}
