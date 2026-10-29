"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { request } from "@/lib/api";
import { Course } from "@/lib/learning";

type Dataset = { symbol: string; timeframes: string[]; first_date: string; last_date: string };
export default function TradingExercise({ course, lessonId }: { course: Course; lessonId: string }) {
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [symbol, setSymbol] = useState("");
  const [timeframe, setTimeframe] = useState("");
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  useEffect(() => { api.getSymbols().then(data => { setDatasets(data); setSymbol(data[0]?.symbol || ""); setTimeframe(data[0]?.timeframes[0] || ""); }).catch(e => setError(e.message)).finally(() => setLoaded(true)); }, []);
  const selected = datasets.find(d => d.symbol === symbol);
  async function upload(file: File) {
    if (file.size > 10 * 1024 * 1024) { setError("Choose a dataset under 10 MB."); return; }
    setUploading(true); setError("");
    try {
      const body = new FormData(); body.append("file", file);
      const result = await request<{ inserted: number; duplicates_skipped: number; errors: string[] }>("/data/upload", { method: "POST", body });
      setUploadStatus(`${result.inserted} candles imported, ${result.duplicates_skipped} duplicates skipped. ${result.errors.slice(0, 3).join(" ")}`);
      const data = await api.getSymbols(); setDatasets(data); setSymbol(data[0]?.symbol || ""); setTimeframe(data[0]?.timeframes[0] || "");
    } catch (e) { setError((e as Error).message); }
    finally { setUploading(false); }
  }
  const query = new URLSearchParams({ course: course.id, lesson: lessonId, symbol, timeframe, start: selected?.first_date.slice(0, 10) || "", end: selected?.last_date.slice(0, 10) || "" });
  return <section className="card" style={{ marginTop: 20 }}><h2>{course.practice_mode === "backtest" ? "Backtesting exercise" : "Replay exercise"}</h2>
    <p>{course.practice_mode === "backtest" ? "Write an entry and exit rule. Test a baseline, then change one parameter and compare actual return, win rate, profit factor, drawdown and trade count. Keep costs and the evaluation period consistent." : "Write an entry, stop, target and share count before revealing the next candle. Pause or step through Replay, place simulated orders, then compare fills and decisions against your plan."}</p>
    <p>Save your decision review in the lesson notes. Simulated outcomes are educational examples and do not guarantee future performance.</p>
    {!loaded && <p role="status">Loading available historical datasets…</p>}
    {error && <p className="learn-error" role="alert">Could not load datasets: {error}</p>}
    {loaded && !error && !datasets.length && <p>No stored historical datasets are available. Upload a permitted historical dataset below to start. Training exercises use stored data and never substitute demo candles.</p>}
    <details><summary>Import historical stock data</summary><p>Use a CSV or JSON file you are permitted to use. Required fields: symbol, timestamp, open, high, low, close, volume, timeframe. CSV timestamps must use ISO dates; timeframes include 1D, 1h and 1m. No market history or performance results are invented for this exercise.</p><label>Historical dataset file<input type="file" accept=".csv,.json" disabled={uploading} onChange={e => { const file = e.target.files?.[0]; if (file) void upload(file); }} /></label><p role="status">{uploading ? "Importing dataset…" : uploadStatus}</p></details>
    {selected && <><div className="learn-filters"><label>Historical dataset<select value={symbol} onChange={e => { const d = datasets.find(d => d.symbol === e.target.value)!; setSymbol(d.symbol); setTimeframe(d.timeframes[0]); }}>{datasets.map(d => <option key={d.symbol}>{d.symbol}</option>)}</select></label><label>Dataset timeframe<select value={timeframe} onChange={e => setTimeframe(e.target.value)}>{selected.timeframes.map(t => <option key={t}>{t}</option>)}</select></label></div><p className="learn-meta">Stored range: {selected.first_date.slice(0, 10)} – {selected.last_date.slice(0, 10)}. Select dates within this range in the practice workspace.</p><Link className="learn-button" href={`/${course.practice_mode === "backtest" ? "backtest" : "replay"}?${query}`}>Open {course.practice_mode === "backtest" ? "Backtest" : "Replay"} exercise →</Link></>}
    {!!course.resources?.length && <><h3>Official external reading</h3>{course.resources.map(r => <p key={r.url}><a className="learn-link" href={r.url} target="_blank" rel="noreferrer">{r.provider}: {r.title} ↗</a><br /><span className="learn-meta">{r.usage}</span></p>)}</>}
  </section>;
}
