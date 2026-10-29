"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function LiveMarketTicker({ symbol = "AAPL" }: { symbol?: string }) {
  const [quote, setQuote] = useState<Awaited<ReturnType<typeof api.getLiveQuote>> | null>(null);

  useEffect(() => {
    let cancelled = false;
    const refresh = async () => {
      try {
        const next = await api.getLiveQuote(symbol);
        if (!cancelled) setQuote(next);
      } catch {
        if (!cancelled) setQuote(null);
      }
    };
    refresh();
    const timer = window.setInterval(refresh, 15_000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [symbol]);

  const positive = (quote?.change ?? 0) >= 0;
  return (
    <div className="live-ticker" aria-live="polite">
      <div><span className="live-ticker-label"><i /> MARKET QUOTE · {symbol}</span><strong>{quote ? `$${quote.price.toFixed(2)}` : "Quote unavailable"}</strong></div>
      {quote && <span className={positive ? "up" : "down"}>{positive ? "+" : ""}{quote.change.toFixed(2)} ({positive ? "+" : ""}{quote.percent_change.toFixed(2)}%)</span>}
      <small>{quote?.is_market_open ? "Market open" : "Latest available quote"}</small>
    </div>
  );
}
