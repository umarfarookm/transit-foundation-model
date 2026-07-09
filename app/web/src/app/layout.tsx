import type { Metadata } from "next";
import "./globals.css";
import { Inter } from "next/font/google";
import { cn } from "@/lib/utils";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "UmarTransit-1B | Transit AI Assistant",
  description:
    "AI assistant for public transit systems and GTFS data, powered by UmarTransit-1B",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={cn("font-sans", inter.variable)}>
      <body className="min-h-screen antialiased bg-white">{children}</body>
    </html>
  );
}
