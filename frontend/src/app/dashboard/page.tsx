"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useState } from "react";
import ProtectedRoute from "@/components/ProtectedRoute";
import { useAuth } from "@/contexts/AuthContext";
import { api, type DashboardSummary, type DashboardRange } from "@/lib/api";
import { dashboardData } from "@/lib/dashboard-cache";

const Charts = dynamic(() => import("@/components/DashboardCharts"), {
  ssr: false, loading: () => <div className="dashboard-chart-placeholder skeleton" role="status">Loading performance charts…</div>,
});
const money = (value: number | null | undefined) => value == null ? "—" : value.toLocaleString("en-US", { style: "currency", currency: "USD" });

function Dashboard({ userId, username }: { userId: string; username: string }) {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [updatedAt, setUpdatedAt] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  const [revision, setRevision] = useState(0);
  const [range, setRange] = useState<DashboardRange>("30D");
  useEffect(() => {
    let active = true;
    async function load(force = false) {
      setBusy(true); setError("");
      try {
        const result = await dashboardData(`${userId}:summary`, api.getDashboardSummary, force);
        if (active) { setData(result.value); setUpdatedAt(result.updatedAt); }
      } catch (reason) { if (active) setError(reason instanceof Error ? reason.message : "Could not load dashboard."); }
      finally { if (active) setBusy(false); }
    }
    void load(revision > 0);
    const refresh = () => { void load(true); };
    window.addEventListener("dashboard-invalidated", refresh);
    return () => { active = false; window.removeEventListener("dashboard-invalidated", refresh); };
  }, [userId, revision]);

  const hasTrades = !!data?.total_trades;
  const metrics = [
    ["Paper equity", money(data?.equity), "Cash plus open positions valued at entry cost; excludes unrealized market movements."],
    ["Realized P&L", money(data?.realized_pnl), "Persisted realized P&L from sell fills, after exit commissions. Entry fees are reflected in equity."],
    ["Win rate", hasTrades ? `${data!.win_rate.toFixed(1)}%` : "—", "Profitable sell fills divided by all sell fills, including partial exits."],
    ["Open positions", data ? String(data.open_positions) : "—", "Symbols with a positive quantity in your paper account."],
    ["Profit factor", data?.profit_factor == null ? "—" : data.profit_factor.toFixed(2), "Gross realized profits divided by absolute realized losses. Unavailable until a loss exists."],
    ["Expectancy", hasTrades ? money(data!.expectancy) : "—", "Average realized P&L per sell fill, including partial exits."],
    ["Average winner", hasTrades && data!.average_win > 0 ? money(data!.average_win) : "—", "Average P&L of profitable sell fills."],
    ["Average loser", hasTrades && data!.average_loss < 0 ? money(data!.average_loss) : "—", "Average P&L of losing sell fills."],
  ];
  return <div className="dashboard-page dashboard-upgraded">
    <header className="page-heading"><div><div className="eyebrow">PAPER TRADING ANALYTICS</div><h1>Welcome back, {username}</h1><p>Your recorded trades, performance, and risk in one place.</p></div><span className="paper-badge">PAPER ACCOUNT</span></header>
    <div className="dashboard-status"><p role="status">{busy ? "Updating dashboard…" : updatedAt ? <>Last updated <time dateTime={new Date(updatedAt).toISOString()}>{new Date(updatedAt).toLocaleString()}</time></> : "Account data unavailable"}</p><button disabled={busy} onClick={() => setRevision(v => v + 1)}>Refresh</button></div>
    {error && <div className="dashboard-error" role="alert"><p>{error} {data ? "Showing the last successful data." : "Account values could not be loaded."}</p><button disabled={busy} onClick={() => setRevision(v => v + 1)}>Retry</button></div>}
    <section className="metric-grid" aria-label="Paper trading metrics" aria-busy={busy}>{metrics.map(([label, value, explanation], index) => <article className={`metric-card ${index < 4 ? "metric-primary" : ""}`} key={label}><span>{label}</span>{busy && !data ? <div className="skeleton metric-skeleton" aria-label="Loading value" /> : <strong>{value}</strong>}<details><summary>About {label.toLowerCase()}</summary><p>{explanation}</p></details></article>)}</section>
    {data && !hasTrades && <section className="terminal-panel dashboard-empty"><h2>Your trading story starts here</h2><p>No closed paper trades yet. Place a trade, then close it to build performance statistics.</p><Link className="primary-button" href="/markets">Place a paper trade</Link></section>}
    <section className="terminal-panel dashboard-panel"><div className="panel-heading"><h2>Recorded performance</h2><div className="dashboard-ranges" role="group" aria-label="Performance date range">{(["7D", "30D", "All"] as const).map(value => <button key={value} aria-pressed={range === value} onClick={() => setRange(value)}>{value}</button>)}</div></div><p className="dashboard-note">Persisted snapshots after fills, valued at entry cost. Drawdown uses the highest recorded equity across all history. No live market valuation.</p><Charts key={`${userId}:${range}:${revision}`} userId={userId} range={range} force={revision > 0} /></section>
    <section className="dashboard-columns">
      <article className="terminal-panel dashboard-panel"><div className="panel-heading"><h2>Recent closed trades</h2><Link href="/journal">Open journal →</Link></div><p className="dashboard-note">Latest five sell fills, including partial exits. P&L includes exit commissions.</p>{data?.recent_trades.length ? <div className="dashboard-table-wrap"><table className="dashboard-trades"><caption className="sr-only">Latest closed paper trade fills</caption><thead><tr><th scope="col">Symbol</th><th scope="col">Closed</th><th scope="col">Realized P&L</th></tr></thead><tbody>{data.recent_trades.map(trade => <tr key={trade.id}><th scope="row">{trade.symbol}</th><td><time dateTime={trade.timestamp}>{new Date(trade.timestamp).toLocaleString()}</time></td><td className={trade.realized_pnl < 0 ? "loss" : "gain"}>{money(trade.realized_pnl)}</td></tr>)}</tbody></table></div> : <p>{busy ? "Loading trades…" : error ? "Recent trades unavailable." : "No closed trades yet."}</p>}</article>
      <article className="terminal-panel dashboard-panel"><div className="panel-heading"><h2>Risk overview</h2><Link href="/settings">Risk settings →</Link></div><dl className="dashboard-risk"><div><dt>Exposure at entry cost</dt><dd>{money(data?.risk.exposure)}</dd></div><div><dt>Today’s realized P&L (UTC)</dt><dd>{money(data?.risk.daily_pnl)}</dd></div><div><dt>Daily loss limit</dt><dd>{money(data?.risk.daily_loss_limit)}</dd></div><div><dt>Daily loss limit used</dt><dd>{data?.risk.daily_loss_used_percent == null ? "—" : `${data.risk.daily_loss_used_percent.toFixed(1)}%`}</dd></div><div><dt>Risk violations · all time</dt><dd>{data?.risk_violations ?? "—"}</dd></div></dl>{data?.risk.daily_loss_used_percent != null && <progress aria-label="Daily loss limit used" value={Math.min(100, data.risk.daily_loss_used_percent)} max={100} />}<details><summary>How risk is calculated</summary><p>Exposure is quantity × average entry price across open positions. Daily loss usage is net realized loss since midnight UTC divided by entry-cost equity × your configured daily loss percentage, matching order checks. Usage can exceed 100%. Violations count recorded rule failures. Missing account or risk settings appear as —.</p></details></article>
    </section>
    <nav className="workflow-links dashboard-workflow" aria-label="Continue trading workflow"><Link href="/settings">Set risk profile</Link><Link href="/markets">Place a paper trade</Link><Link href="/journal">Review journal</Link><Link href="/training">Ask the AI coach</Link></nav>
    <p className="educational-disclaimer">Educational use only. Simulated paper trading.</p>
  </div>;
}

export default function DashboardPage() {
  const { user } = useAuth();
  return <ProtectedRoute>{user && <Dashboard key={user.id} userId={user.id} username={user.username} />}</ProtectedRoute>;
}
