"use client";

import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, type DashboardHistory, type DashboardRange } from "@/lib/api";
import { dashboardData } from "@/lib/dashboard-cache";

export default function DashboardCharts({ userId, range, force = false }: { userId: string; range: DashboardRange; force?: boolean }) {
  const [history, setHistory] = useState<DashboardHistory | null>(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    async function load(force = false) {
      setError("");
      try {
        const result = await dashboardData(`${userId}:history:${range}`, () => api.getDashboardHistory(range), force);
        if (active) setHistory(result.value);
      } catch { if (active) setError("Could not load performance history."); }
    }
    void load(force || attempt > 0);
    const refresh = () => { void load(true); };
    window.addEventListener("dashboard-invalidated", refresh);
    return () => { active = false; window.removeEventListener("dashboard-invalidated", refresh); };
  }, [userId, range, attempt, force]);
  if (error) return <div className="dashboard-chart-placeholder" role="alert"><p>{error}</p><button onClick={() => setAttempt(v => v + 1)}>Retry charts</button></div>;
  if (!history) return <div className="dashboard-chart-placeholder skeleton" role="status">Loading recorded history…</div>;
  if (history.points.length < 2) return <div className="dashboard-chart-placeholder"><p>Not enough recorded history in this range. At least two snapshots are needed.</p><p>Snapshots are saved after paper fills. Try All or return after more trades.</p></div>;
  const points = history.points.map(point => ({ ...point, time: new Date(point.timestamp).getTime() }));
  return <><p className="dashboard-note">{history.observation_count} recorded observations{history.observation_count > 500 ? "; chart shows 500 sampled points" : ""}. Maximum recorded drawdown in range: {history.max_drawdown?.toFixed(2)}%.</p><div className="dashboard-chart-grid">{(["equity", "drawdown"] as const).map(kind => <figure key={kind}><figcaption>{kind === "equity" ? "Equity · USD" : "Drawdown · %"}</figcaption><div className="dashboard-chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={points} accessibilityLayer margin={{ top: 12, right: 12, left: 0, bottom: 12 }}><CartesianGrid stroke="#23404c" strokeDasharray="3 3" /><XAxis dataKey="time" type="number" domain={["dataMin", "dataMax"]} tickFormatter={value => new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric" })} tick={{ fill: "#a9c5ca", fontSize: 11 }} minTickGap={40} /><YAxis width={68} tick={{ fill: "#a9c5ca", fontSize: 11 }} tickFormatter={value => kind === "equity" ? `$${Number(value).toLocaleString(undefined, { notation: "compact" })}` : `${value}%`} domain={kind === "equity" ? ["auto", "auto"] : ["auto", 0]} /><Tooltip labelFormatter={value => new Date(Number(value)).toLocaleString()} contentStyle={{ background: "#06141b", border: "1px solid #52747f", color: "#e8fdff" }} formatter={value => [kind === "equity" ? `$${Number(value).toLocaleString()}` : `${Number(value).toFixed(2)}%`, kind === "equity" ? "Equity" : "Drawdown"]} /><Area type="linear" dataKey={kind} stroke={kind === "equity" ? "#00e5b0" : "#ff7c92"} fill={kind === "equity" ? "#00e5b0" : "#ff7c92"} fillOpacity={0.12} strokeWidth={2} isAnimationActive={false} /></AreaChart></ResponsiveContainer></div></figure>)}</div><details><summary>View chart data as a table</summary><div className="dashboard-table-wrap dashboard-history-table"><table className="dashboard-trades"><caption>Displayed recorded snapshots</caption><thead><tr><th scope="col">Time</th><th scope="col">Equity (USD)</th><th scope="col">Drawdown</th></tr></thead><tbody>{history.points.map((point, index) => <tr key={index}><th scope="row">{new Date(point.timestamp).toLocaleString()}</th><td>{point.equity.toFixed(2)}</td><td>{point.drawdown.toFixed(2)}%</td></tr>)}</tbody></table></div></details></>;
}
