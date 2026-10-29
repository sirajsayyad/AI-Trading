"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import CoachChat from "@/components/CoachChat";
import LearningCatalog from "@/components/LearningCatalog";
import LiveMarketTicker from "@/components/LiveMarketTicker";

export default function TrainingPage() {
  const [chatOpen, setChatOpen] = useState(false);
  const [behaviorFlags, setBehaviorFlags] = useState<Array<Record<string, unknown>>>([]);

  const analyzeBehavior = async () => {
    try {
      const res = await api.analyzeBehavior(sampleTrades, 100000);
      setBehaviorFlags(res.flags as Array<Record<string, unknown>>);
    } catch {
      setBehaviorFlags([]);
    }
  };

  return (
    <div>
      <div className="page-heading" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "32px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 700, marginBottom: "8px" }}>AI Training</h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "15px" }}>
            AI trading lessons, historical replay exercises, and strategy backtesting.
          </p>
        </div>
        <button onClick={() => setChatOpen(!chatOpen)} style={{
          padding: "10px 20px", borderRadius: "10px", border: "none",
          background: "var(--gradient-primary)", color: "white", fontWeight: 600,
          fontSize: "14px", cursor: "pointer", display: "flex", alignItems: "center", gap: "8px",
        }}>
          🤖 AI Coach {chatOpen ? "✕" : ""}
        </button>
      </div>

      <LiveMarketTicker symbol="AAPL" />

      <div className="training-layout" style={{ display: "grid", gridTemplateColumns: chatOpen ? "1fr 380px" : "1fr", gap: "20px" }}>
        <div>
          <LearningCatalog />

          {/* Behavioral Analytics */}
          <div style={{ marginBottom: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
              <h2 style={{ fontSize: "20px", fontWeight: 700 }}>Behavioral Analytics</h2>
              <button onClick={analyzeBehavior} style={{
                padding: "8px 16px", borderRadius: "8px", border: "1px solid var(--color-border)",
                background: "transparent", color: "var(--color-text-secondary)",
                fontSize: "13px", fontWeight: 500, cursor: "pointer",
              }}>
                🔍 Analyze (Demo)
              </button>
            </div>
            {behaviorFlags.length > 0 ? (
              <div style={{ display: "grid", gap: "12px" }}>
                {behaviorFlags.map((flag, i) => (
                  <div key={i} className="card" style={{ padding: "16px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
                      <span style={{
                        padding: "3px 8px", borderRadius: "6px", fontSize: "11px", fontWeight: 600,
                        textTransform: "uppercase",
                        background: flag.severity === "high" ? "rgba(239,68,68,0.1)" : flag.severity === "medium" ? "rgba(245,158,11,0.1)" : "rgba(99,102,241,0.1)",
                        color: flag.severity === "high" ? "#ef4444" : flag.severity === "medium" ? "#f59e0b" : "#6366f1",
                      }}>
                        {flag.severity as string}
                      </span>
                      <span style={{ fontSize: "14px", fontWeight: 600 }}>
                        {(flag.flag_type as string).replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase())}
                      </span>
                    </div>
                    <p style={{ fontSize: "13px", color: "var(--color-text-secondary)", marginBottom: "8px" }}>
                      {flag.description as string}
                    </p>
                    <p style={{ fontSize: "12px", color: "var(--color-accent-primary)", fontWeight: 500 }}>
                      💡 {flag.recommendation as string}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="card" style={{ textAlign: "center", padding: "32px", opacity: 0.7 }}>
                <p style={{ fontSize: "14px", color: "var(--color-text-muted)" }}>
                  Click &quot;Analyze&quot; to run behavioral detection on sample trade history
                </p>
              </div>
            )}
          </div>
        </div>

        {chatOpen && <aside style={{ minWidth: 0 }}><CoachChat /></aside>}
      </div>
    </div>
  );
}

// ─── Sample Data ───
const sampleTrades = [
  { symbol: "AAPL", side: "long", entry_price: 150, exit_price: 148, quantity: 100, entry_time: "2024-01-01T10:00:00Z", exit_time: "2024-01-01T14:00:00Z", pnl: -200, duration_hours: 4 },
  { symbol: "AAPL", side: "long", entry_price: 147, exit_price: 144, quantity: 200, entry_time: "2024-01-01T14:30:00Z", exit_time: "2024-01-01T16:00:00Z", pnl: -600, duration_hours: 1.5 },
  { symbol: "AAPL", side: "long", entry_price: 143, exit_price: 140, quantity: 400, entry_time: "2024-01-01T16:30:00Z", exit_time: "2024-01-02T10:00:00Z", pnl: -1200, duration_hours: 17.5 },
  { symbol: "AAPL", side: "long", entry_price: 141, exit_price: 145, quantity: 50, entry_time: "2024-01-03T10:00:00Z", exit_time: "2024-01-03T15:00:00Z", pnl: 200, duration_hours: 5 },
];
