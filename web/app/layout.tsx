import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Neural Chess",
  description: "Play against a CPU-first neural chess engine in a focused glass interface.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
