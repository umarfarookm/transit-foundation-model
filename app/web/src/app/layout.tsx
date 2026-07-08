import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "UmarTransit-1B",
  description: "AI assistant for public transit systems and GTFS data",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen">{children}</body>
    </html>
  );
}
