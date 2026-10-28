import type { Metadata } from "next";
import "./globals.css";
import ClientLayout from "@/components/ClientLayout";

export const metadata: Metadata = {
  title: "AITrade — AI Trading Training, Replay & Backtesting Platform",
  description:
    "Practice, learn, and validate trading strategies with AI-powered coaching, historical market replay, and quantitative backtesting.",
  keywords: ["trading", "backtesting", "AI", "coaching", "market replay", "quantitative trading"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body>
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  );
}
