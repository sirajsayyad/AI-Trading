"use client";

import { useState } from "react";
import { api } from "@/lib/api";

interface BacktestResults {
  total_return: number;
  total_return_pct: number;
  cagr: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  max_drawdown_pct: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  profit_factor: number;
  avg_win: number;
  avg_loss: number;
  initial_capital: number;
  final_equity: number;
  equity_curve: Array<{ timestamp: string; equity: number }>;
  trades: Array<{
    symbol: string; side: string; entry_price: number; exit_price: number;
    quantity: number; pnl: number; entry_time: string; exit_time: string; duration_hours: number;
  }>;
}

export default function BacktestPage() {
  const [symbol, setSymbol] = useState("AAPL");
  const [strategy, setStrategy] = useState("sma_crossover");
  const [timeframe, setTimeframe] = useState("1D");
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2024-01-01");
  const [capital, setCapital] = useState(100000);
  const [shortPeriod, setShortPeriod] = useState(10);
  const [longPeriod, setLongPeriod] = useState(30);
  const [results, setResults] = useState<BacktestResults | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState<"results" | "trades" | "montecarlo">("results");
  const [monteCarloData, setMonteCarloData] = useState<Record<string, unknown> | null>(null);
  const [mcLoading, setMcLoading] = useState(false);

  const runBacktest = async () => {
    setLoading(true);
    setError("");
    setResults(null);
    try {
      const res = await api.runBacktest({
        symbol, strategy_name: strategy, timeframe,
        start_date: startDate, end_date: endDate,
        initial_capital: capital,
        strategy_params: { short_period: shortPeriod, long_period: longPeriod, quantity: 100 },
      }) as { results: BacktestResults };
      setResults(res.results);
      setActiveTab("results");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Backtest failed");
    } finally {
      setLoading(false);
    }
  };

  const runMonteCarlo = async () => {
    setMcLoading(true);
    try {
      const res = await api.runMonteCarlo({
        symbol, strategy_name: strategy, timeframe,
        start_date: startDate, end_date: endDate,
        initial_capital: capital,
        strategy_params: { short_period: shortPeriod, long_period: longPeriod, quantity: 100 },
        simulations: 1000,
      });
      setMonteCarloData(res as Record<string, unknown>);
      setActiveTab("montecarlo");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Monte Carlo failed");
    } finally {
      setMcLoading(false);
    }
  };

  const metricCard = (label: string, value: string, color: string, subtext?: string) => (
    <div style={{
      background: "var(--gradient-card)", border: "1px solid var(--color-border)",
      borderRadius: "14px", padding: "20px", position: "relative", overflow: "hidden",
    }}>
      <div style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "2px",
        background: `linear-gradient(90deg, ${color}, transparent)` }} />
      <div style={{ fontSize: "12px", color: "var(--color-text-muted)", fontWeight: 500, textTransform: "uppercase",
        letterSpacing: "0.05em", marginBottom: "6px" }}>{label}</div>
      <div style={{ fontSize: "24px", fontWeight: 700, fontFamily: "var(--font-mono)", color }}>{value}</div>
      {subtext && <div style={{ fontSize: "11px", color: "var(--color-text-muted)", marginTop: "4px" }}>{subtext}</div>}
    </div>
  );

  return (
    <div>
      <div style={{ marginBottom: "32px" }}>
        <h1 style={{ fontSize: "28px", fontWeight: 700, marginBottom: "8px" }}>Strategy Backtesting</h1>
        <p style={{ color: "var(--color-text-secondary)", fontSize: "15px" }}>
          Configure and run event-driven backtests with walk-forward analysis and Monte Carlo simulation.
        </p>
      </div>

      <div className="backtest-layout" style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: "24px", alignItems: "start" }}>
        {/* ─── Config Panel ─── */}
        <div className="card sticky-panel" style={{ position: "sticky", top: "80px" }}>
          <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "20px" }}>Configuration</h3>
          
          {/* Symbol */}
          <div style={{ marginBottom: "16px" }}>
            <label style={labelStyle}>Symbol</label>
            <input value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} style={inputStyle} placeholder="AAPL" />
          </div>

          {/* Strategy */}
          <div style={{ marginBottom: "16px" }}>
            <label style={labelStyle}>Strategy</label>
            <select value={strategy} onChange={e => setStrategy(e.target.value)} style={inputStyle}>
              <option value="sma_crossover">SMA Crossover</option>
            </select>
          </div>

          {/* Timeframe */}
          <div style={{ marginBottom: "16px" }}>
            <label style={labelStyle}>Timeframe</label>
            <select value={timeframe} onChange={e => setTimeframe(e.target.value)} style={inputStyle}>
              {["1m","5m","15m","1h","4h","1D","1W"].map(tf => (
                <option key={tf} value={tf}>{tf}</option>
              ))}
            </select>
          </div>

          {/* Date Range */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginBottom: "16px" }}>
            <div>
              <label style={labelStyle}>Start</label>
              <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} style={inputStyle} />
            </div>
            <div>
              <label style={labelStyle}>End</label>
              <input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} style={inputStyle} />
            </div>
          </div>

          {/* Capital */}
          <div style={{ marginBottom: "16px" }}>
            <label style={labelStyle}>Initial Capital ($)</label>
            <input type="number" value={capital} onChange={e => setCapital(Number(e.target.value))} style={inputStyle} />
          </div>

          {/* Strategy Params */}
          <div style={{ padding: "12px", borderRadius: "10px", background: "rgba(99,102,241,0.05)",
            border: "1px solid rgba(99,102,241,0.1)", marginBottom: "16px" }}>
            <div style={{ fontSize: "12px", color: "var(--color-accent-primary)", fontWeight: 600, marginBottom: "10px" }}>
              Strategy Parameters
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
              <div>
                <label style={{ ...labelStyle, fontSize: "11px" }}>Short SMA</label>
                <input type="number" value={shortPeriod} onChange={e => setShortPeriod(Number(e.target.value))}
                  style={inputStyle} min={2} max={200} />
              </div>
              <div>
                <label style={{ ...labelStyle, fontSize: "11px" }}>Long SMA</label>
                <input type="number" value={longPeriod} onChange={e => setLongPeriod(Number(e.target.value))}
                  style={inputStyle} min={5} max={500} />
              </div>
            </div>
          </div>

          {/* Run Button */}
          <button onClick={runBacktest} disabled={loading} style={{
            width: "100%", padding: "12px", borderRadius: "10px", border: "none",
            background: loading ? "var(--color-text-muted)" : "var(--gradient-primary)",
            color: "white", fontWeight: 600, fontSize: "14px", cursor: loading ? "wait" : "pointer",
            transition: "all var(--transition-fast)",
          }}>
            {loading ? "⏳ Running Backtest..." : "▶ Run Backtest"}
          </button>

          {results && (
            <button onClick={runMonteCarlo} disabled={mcLoading} style={{
              width: "100%", padding: "10px", borderRadius: "10px", border: "1px solid var(--color-border)",
              background: "transparent", color: "var(--color-text-secondary)", fontWeight: 500,
              fontSize: "13px", cursor: mcLoading ? "wait" : "pointer", marginTop: "8px",
              transition: "all var(--transition-fast)",
            }}>
              {mcLoading ? "⏳ Simulating..." : "🎲 Monte Carlo (1000 sims)"}
            </button>
          )}

          {error && (
            <div style={{ marginTop: "12px", padding: "10px", borderRadius: "8px",
              background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)",
              color: "var(--color-accent-danger)", fontSize: "13px" }}>
              {error}
            </div>
          )}
        </div>

        {/* ─── Results Panel ─── */}
        <div>
          {loading && (
            <div className="card" style={{ textAlign: "center", padding: "60px" }}>
              <div style={{ fontSize: "40px", marginBottom: "12px" }} className="animate-float">📊</div>
              <div style={{ fontSize: "16px", fontWeight: 600 }}>Running backtest...</div>
              <div style={{ fontSize: "13px", color: "var(--color-text-muted)", marginTop: "4px" }}>
                Processing candles bar-by-bar
              </div>
            </div>
          )}

          {!loading && !results && (
            <div className="card" style={{ textAlign: "center", padding: "80px 40px" }}>
              <div style={{ fontSize: "48px", marginBottom: "16px", opacity: 0.4 }}>📊</div>
              <h3 style={{ fontSize: "18px", fontWeight: 600, marginBottom: "8px" }}>Configure & Run</h3>
              <p style={{ color: "var(--color-text-muted)", fontSize: "14px", maxWidth: "320px", margin: "0 auto" }}>
                Set your strategy parameters and click &quot;Run Backtest&quot; to see results.
              </p>
            </div>
          )}

          {results && (
            <div>
              {/* Tab Bar */}
              <div style={{ display: "flex", gap: "4px", marginBottom: "20px", padding: "4px",
                borderRadius: "12px", background: "var(--color-bg-card)", border: "1px solid var(--color-border)",
                width: "fit-content" }}>
                {(["results", "trades", "montecarlo"] as const).map(tab => (
                  <button key={tab} onClick={() => setActiveTab(tab)} style={{
                    padding: "8px 20px", borderRadius: "8px", border: "none", fontSize: "13px", fontWeight: 500,
                    cursor: "pointer", transition: "all var(--transition-fast)",
                    background: activeTab === tab ? "var(--color-accent-primary)" : "transparent",
                    color: activeTab === tab ? "white" : "var(--color-text-secondary)",
                  }}>
                    {tab === "results" ? "📈 Results" : tab === "trades" ? "📋 Trades" : "🎲 Monte Carlo"}
                  </button>
                ))}
              </div>

              {/* Results Tab */}
              {activeTab === "results" && (
                <div className="animate-fade-in">
                  {/* Metric Cards */}
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "12px", marginBottom: "20px" }}>
                    {metricCard("Total Return", `${results.total_return >= 0 ? "+" : ""}$${results.total_return.toLocaleString("en-US")}`,
                      results.total_return >= 0 ? "#10b981" : "#ef4444", `${(results.total_return_pct * 100).toFixed(2)}%`)}
                    {metricCard("CAGR", `${(results.cagr * 100).toFixed(2)}%`,
                      results.cagr >= 0 ? "#10b981" : "#ef4444")}
                    {metricCard("Sharpe Ratio", results.sharpe_ratio.toFixed(2),
                      results.sharpe_ratio >= 1 ? "#10b981" : results.sharpe_ratio >= 0 ? "#f59e0b" : "#ef4444")}
                    {metricCard("Max Drawdown", `${(results.max_drawdown_pct * 100).toFixed(2)}%`, "#ef4444")}
                    {metricCard("Win Rate", `${(results.win_rate * 100).toFixed(1)}%`,
                      results.win_rate >= 0.5 ? "#10b981" : "#f59e0b")}
                    {metricCard("Profit Factor", results.profit_factor === Infinity ? "∞" : results.profit_factor.toFixed(2),
                      results.profit_factor >= 1.5 ? "#10b981" : results.profit_factor >= 1 ? "#f59e0b" : "#ef4444")}
                    {metricCard("Total Trades", results.total_trades.toString(), "#6366f1",
                      `${results.winning_trades}W / ${results.losing_trades}L`)}
                    {metricCard("Final Equity", `$${results.final_equity.toLocaleString("en-US")}`, "#8b5cf6")}
                  </div>

                  {/* Equity Curve */}
                  <div className="card" style={{ padding: "20px" }}>
                    <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "16px", color: "var(--color-text-secondary)" }}>
                      Equity Curve
                    </h3>
                    <div style={{ height: "300px", position: "relative" }}>
                      <EquityCurveChart data={results.equity_curve} initial={results.initial_capital} />
                    </div>
                  </div>
                </div>
              )}

              {/* Trades Tab */}
              {activeTab === "trades" && (
                <div className="card animate-fade-in" style={{ overflow: "auto" }}>
                  <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "16px" }}>
                    Trade Log ({results.trades.length} trades)
                  </h3>
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid var(--color-border)" }}>
                        {["#", "Side", "Entry", "Exit", "P&L", "Duration"].map(h => (
                          <th key={h} style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600,
                            color: "var(--color-text-muted)", fontSize: "11px", textTransform: "uppercase" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {results.trades.map((t, i) => (
                        <tr key={i} style={{ borderBottom: "1px solid var(--color-border)" }}>
                          <td style={tdStyle}>{i + 1}</td>
                          <td style={tdStyle}>
                            <span style={{ padding: "2px 8px", borderRadius: "4px", fontSize: "11px", fontWeight: 600,
                              background: t.side === "long" ? "rgba(16,185,129,0.1)" : "rgba(239,68,68,0.1)",
                              color: t.side === "long" ? "#10b981" : "#ef4444" }}>
                              {t.side.toUpperCase()}
                            </span>
                          </td>
                          <td style={{ ...tdStyle, fontFamily: "var(--font-mono)" }}>${t.entry_price.toFixed(2)}</td>
                          <td style={{ ...tdStyle, fontFamily: "var(--font-mono)" }}>${t.exit_price.toFixed(2)}</td>
                          <td style={{ ...tdStyle, fontFamily: "var(--font-mono)", fontWeight: 600,
                            color: t.pnl >= 0 ? "#10b981" : "#ef4444" }}>
                            {t.pnl >= 0 ? "+" : ""}${t.pnl.toFixed(2)}
                          </td>
                          <td style={{ ...tdStyle, color: "var(--color-text-muted)" }}>{t.duration_hours.toFixed(1)}h</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Monte Carlo Tab */}
              {activeTab === "montecarlo" && (
                <div className="animate-fade-in">
                  {!monteCarloData ? (
                    <div className="card" style={{ textAlign: "center", padding: "60px" }}>
                      <div style={{ fontSize: "40px", marginBottom: "12px" }}>🎲</div>
                      <p style={{ color: "var(--color-text-muted)" }}>Click &quot;Monte Carlo&quot; to run 1000 simulations</p>
                    </div>
                  ) : (
                    <div>
                      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "12px", marginBottom: "20px" }}>
                        {metricCard("5th Percentile Return",
                          `${((monteCarloData.percentile_returns as Record<string, number>)?.["5th"] * 100).toFixed(2)}%`, "#ef4444", "Worst case")}
                        {metricCard("Median Return",
                          `${((monteCarloData.percentile_returns as Record<string, number>)?.["50th"] * 100).toFixed(2)}%`, "#f59e0b", "Typical")}
                        {metricCard("95th Percentile Return",
                          `${((monteCarloData.percentile_returns as Record<string, number>)?.["95th"] * 100).toFixed(2)}%`, "#10b981", "Best case")}
                      </div>
                      <div className="card" style={{ padding: "20px" }}>
                        <h3 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "12px" }}>
                          Distribution of {monteCarloData.simulations as number} Simulations
                        </h3>
                        <MonteCarloHistogram data={(monteCarloData.distribution as Array<{ return: number }>) || []} />
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── Sub Components ─── */

function EquityCurveChart({ data, initial }: { data: Array<{ timestamp: string; equity: number }>; initial: number }) {
  if (!data.length) return <div style={{ color: "var(--color-text-muted)" }}>No data</div>;

  const equities = data.map(d => d.equity);
  const min = Math.min(...equities) * 0.995;
  const max = Math.max(...equities) * 1.005;
  const range = max - min || 1;
  const w = 800, h = 280;

  const points = data.map((d, i) => {
    const x = (i / (data.length - 1)) * w;
    const y = h - ((d.equity - min) / range) * h;
    return `${x},${y}`;
  }).join(" ");

  const areaPoints = `0,${h} ${points} ${w},${h}`;
  const isProfit = equities[equities.length - 1] >= initial;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", height: "100%" }}>
      <defs>
        <linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={isProfit ? "#10b981" : "#ef4444"} stopOpacity="0.3" />
          <stop offset="100%" stopColor={isProfit ? "#10b981" : "#ef4444"} stopOpacity="0" />
        </linearGradient>
      </defs>
      <polygon points={areaPoints} fill="url(#eqGrad)" />
      <polyline points={points} fill="none" stroke={isProfit ? "#10b981" : "#ef4444"}
        strokeWidth="2" strokeLinejoin="round" />
    </svg>
  );
}

function MonteCarloHistogram({ data }: { data: Array<{ return: number }> }) {
  if (!data.length) return null;

  const returns = data.map(d => d.return * 100);
  const min = Math.min(...returns);
  const max = Math.max(...returns);
  const bucketCount = 30;
  const bucketSize = (max - min) / bucketCount || 1;

  const buckets = new Array(bucketCount).fill(0);
  returns.forEach(r => {
    const idx = Math.min(Math.floor((r - min) / bucketSize), bucketCount - 1);
    buckets[idx]++;
  });

  const maxBucket = Math.max(...buckets);
  const w = 800, h = 200;
  const barW = w / bucketCount;

  return (
    <svg viewBox={`0 0 ${w} ${h + 30}`} style={{ width: "100%", height: "200px" }}>
      {buckets.map((count, i) => {
        const barH = (count / maxBucket) * h;
        const val = min + i * bucketSize;
        const color = val >= 0 ? "rgba(16,185,129,0.6)" : "rgba(239,68,68,0.6)";
        return (
          <rect key={i} x={i * barW + 1} y={h - barH} width={barW - 2} height={barH}
            fill={color} rx="2" />
        );
      })}
      <text x="0" y={h + 20} fill="var(--color-text-muted)" fontSize="10">{min.toFixed(1)}%</text>
      <text x={w} y={h + 20} fill="var(--color-text-muted)" fontSize="10" textAnchor="end">{max.toFixed(1)}%</text>
    </svg>
  );
}

/* ─── Shared Styles ─── */
const labelStyle: React.CSSProperties = {
  display: "block", fontSize: "12px", fontWeight: 500, color: "var(--color-text-muted)",
  marginBottom: "4px", textTransform: "uppercase", letterSpacing: "0.04em",
};

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "8px 12px", borderRadius: "8px", fontSize: "14px",
  border: "1px solid var(--color-border)", background: "var(--color-bg-secondary)",
  color: "var(--color-text-primary)", outline: "none",
};

const tdStyle: React.CSSProperties = {
  padding: "10px 12px", verticalAlign: "middle",
};
