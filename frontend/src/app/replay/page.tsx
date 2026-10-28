"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { api, getWsUrl } from "@/lib/api";

interface CandleMsg {
  index: number;
  total: number;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  symbol?: string;
  date_display?: string;
  fills?: Array<{ order_id: string; side: string; quantity: number; price: number }>;
  positions?: Record<string, { quantity: number; avg_entry: number; unrealized_pnl: number; realized_pnl: number }>;
}

interface SessionSummary {
  total_bars: number;
  bars_viewed: number;
  orders_placed: number;
  total_pnl: number;
  net_pnl: number;
}

interface TradeRecord {
  order_id: string;
  side: string;
  quantity: number;
  price: number;
  timestamp: string;
}

export default function ReplayPage() {
  const [phase, setPhase] = useState<"config" | "playing" | "summary">("config");
  const [symbol, setSymbol] = useState("AAPL");
  const [timeframe, setTimeframe] = useState("1D");
  const [startDate, setStartDate] = useState("2023-01-01");
  const [speed, setSpeed] = useState(5);
  const [blindMode, setBlindMode] = useState(false);
  const [candles, setCandles] = useState<CandleMsg[]>([]);
  const [currentCandle, setCurrentCandle] = useState<CandleMsg | null>(null);
  const [hoveredCandle, setHoveredCandle] = useState<CandleMsg | null>(null);
  const [selectedCandle, setSelectedCandle] = useState<CandleMsg | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isPaused, setIsPaused] = useState(false);
  const [positions, setPositions] = useState<Record<string, unknown>>({});
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [feedback, setFeedback] = useState("");
  const [trades, setTrades] = useState<TradeRecord[]>([]);
  const [orderQty, setOrderQty] = useState(100);
  const [orderType, setOrderType] = useState("market");
  const [orderPrice, setOrderPrice] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const wsRef = useRef<WebSocket | null>(null);

  const startSession = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.createReplaySession({
        symbol, timeframe, start_date: startDate,
        speed_multiplier: speed, blind_mode: blindMode,
      }) as { session_id: string };
      setCandles([]);
      setTrades([]);
      setCurrentCandle(null);
      setHoveredCandle(null);
      setSelectedCandle(null);
      setElapsedSeconds(0);
      setIsPaused(false);
      setPositions({});
      setPhase("playing");
      connectWebSocket(res.session_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create session");
    } finally {
      setLoading(false);
    }
  };

  const connectWebSocket = useCallback((sid: string) => {
    const ws = new WebSocket(getWsUrl(sid));
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "candle") {
        const candle = msg.data as CandleMsg;
        setCandles(prev => [...prev, candle]);
        setCurrentCandle(candle);
        if (candle.positions) setPositions(candle.positions);
        if (candle.fills?.length) {
          setTrades(prev => [...prev, ...candle.fills!.map(fill => ({ ...fill, timestamp: candle.timestamp }))]);
        }
      } else if (msg.type === "completed") {
        setSummary(msg.summary);
        setPhase("summary");
      }
    };

    ws.onerror = () => setError("WebSocket connection error");
    ws.onclose = () => {};
  }, []);

  const sendControl = (action: string, value?: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "control", action, value }));
      if (action === "pause") setIsPaused(true);
      if (action === "resume") setIsPaused(false);
    }
  };

  const placeOrder = (side: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: "order", side, order_type: orderType,
        quantity: orderQty, price: orderPrice ? parseFloat(orderPrice) : undefined,
      }));
    }
  };

  useEffect(() => {
    return () => { wsRef.current?.close(); };
  }, []);

  useEffect(() => {
    if (phase !== "playing" || isPaused) return;
    const timer = window.setInterval(() => setElapsedSeconds(value => value + 1), 1000);
    return () => window.clearInterval(timer);
  }, [phase, isPaused]);

  const progress = currentCandle ? ((currentCandle.index + 1) / currentCandle.total) * 100 : 0;

  // Mini chart SVG
  const chartCandles = candles.slice(-80);
  const renderChart = () => {
    if (!chartCandles.length) return <p role="status">Waiting for the first candle…</p>;
    const prices = chartCandles.flatMap(c => [c.high, c.low]);
    const padding = (Math.max(...prices) - Math.min(...prices)) * 0.08 || 1;
    const minP = Math.min(...prices) - padding;
    const maxP = Math.max(...prices) + padding;
    const range = maxP - minP || 1;
    const w = 820, h = 340;
    const barW = Math.max(4, w / chartCandles.length - 2);

    return (
      <svg viewBox="0 0 900 390" role="img" aria-label="Replay candlestick chart with price and UTC date and time axes. Select a candle below for its report." style={{ width: "100%", cursor: "crosshair" }} onClick={() => setSelectedCandle(hoveredCandle || currentCandle)} onMouseMove={(event) => {
        const rect = event.currentTarget.getBoundingClientRect();
        const chartX = ((event.clientX - rect.left) / rect.width) * 900;
        const index = Math.max(0, Math.min(chartCandles.length - 1, Math.floor((chartX / w) * chartCandles.length)));
        setHoveredCandle(chartCandles[index]);
      }} onMouseLeave={() => setHoveredCandle(null)}>
        {Array.from({ length: 6 }, (_, i) => {
          const y = (i / 5) * h;
          return <g key={`price-${i}`}><line x1="0" x2={w} y1={y} y2={y} stroke="var(--color-border)" /><text x={w + 8} y={y + 12} fill="var(--color-text-secondary)" fontSize="12">${(maxP - (i / 5) * range).toFixed(2)}</text></g>;
        })}
        {!blindMode && chartCandles.filter((_, i) => i % Math.max(1, Math.ceil(chartCandles.length / 5)) === 0).map(c => {
          const x = (chartCandles.indexOf(c) / chartCandles.length) * w;
          return <g key={`time-${c.index}`}><text x={x} y="363" fill="var(--color-text-secondary)" fontSize="12">{formatCandleTime(c.timestamp, true)}</text><text x={x} y="382" fill="var(--color-text-muted)" fontSize="11">{formatCandleTime(c.timestamp, false)}</text></g>;
        })}
        {currentCandle && <g><line x1="0" x2={w} y1={h - ((currentCandle.close - minP) / range) * h} y2={h - ((currentCandle.close - minP) / range) * h} stroke="var(--color-accent-primary)" strokeDasharray="5 4" /><title>Latest replay market price: ${currentCandle.close.toFixed(2)}</title></g>}
        {chartCandles.map((c, i) => {
          const x = (i / chartCandles.length) * w;
          const oY = h - ((c.open - minP) / range) * h;
          const cY = h - ((c.close - minP) / range) * h;
          const hY = h - ((c.high - minP) / range) * h;
          const lY = h - ((c.low - minP) / range) * h;
          const bullish = c.close >= c.open;
          const color = bullish ? "#10b981" : "#ef4444";
          const bodyTop = Math.min(oY, cY);
          const bodyH = Math.max(1, Math.abs(oY - cY));

          return (
            <g key={i}>
              <title>{blindMode ? `Bar ${c.index + 1}` : `${formatCandleTime(c.timestamp, true)} ${formatCandleTime(c.timestamp, false)} UTC`}: Open ${c.open.toFixed(2)}, High ${c.high.toFixed(2)}, Low ${c.low.toFixed(2)}, Close ${c.close.toFixed(2)}</title>
              <line x1={x + barW / 2} y1={hY} x2={x + barW / 2} y2={lY}
                stroke={color} strokeWidth="1" />
              <rect x={x} y={bodyTop} width={barW} height={bodyH}
                fill={bullish ? color : color} rx="1" />
            </g>
          );
        })}
      </svg>
    );
  };

  // ─── Config Phase ───
  if (phase === "config") {
    return (
      <div>
        <div style={{ marginBottom: "32px" }}>
          <h1 style={{ fontSize: "28px", fontWeight: 700, marginBottom: "8px" }}>Market Replay</h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "15px" }}>
            Practice trading on historical data with live candle streaming and simulated order execution.
          </p>
        </div>

        <div style={{ maxWidth: "500px" }}>
          <div className="card">
            <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "20px" }}>New Session</h3>

            <div style={{ marginBottom: "16px" }}>
              <label style={labelStyle}>Symbol</label>
              <input value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())} style={inputStyle} />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginBottom: "16px" }}>
              <div>
                <label style={labelStyle}>Timeframe</label>
                <select value={timeframe} onChange={e => setTimeframe(e.target.value)} style={inputStyle}>
                  {["1m","5m","15m","1h","1D"].map(tf => <option key={tf} value={tf}>{tf}</option>)}
                </select>
              </div>
              <div>
                <label style={labelStyle}>Speed</label>
                <select value={speed} onChange={e => setSpeed(Number(e.target.value))} style={inputStyle}>
                  {[1, 5, 10, 25, 50, 100].map(s => <option key={s} value={s}>{s}x</option>)}
                </select>
              </div>
            </div>

            <div style={{ marginBottom: "16px" }}>
              <label style={labelStyle}>Start Date</label>
              <input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} style={inputStyle} />
            </div>

            <label style={{
              display: "flex", alignItems: "center", gap: "10px", marginBottom: "20px",
              cursor: "pointer", fontSize: "14px", color: "var(--color-text-secondary)",
            }}>
              <div style={{
                width: "40px", height: "22px", borderRadius: "11px", position: "relative",
                background: blindMode ? "var(--color-accent-primary)" : "var(--color-bg-secondary)",
                border: "1px solid var(--color-border)", transition: "all var(--transition-fast)",
              }} onClick={() => setBlindMode(!blindMode)}>
                <div style={{
                  width: "16px", height: "16px", borderRadius: "50%", background: "white",
                  position: "absolute", top: "2px", left: blindMode ? "20px" : "2px",
                  transition: "all var(--transition-fast)",
                }} />
              </div>
              Blind Mode (hide symbol & dates)
            </label>

            <button onClick={startSession} disabled={loading} style={{
              width: "100%", padding: "14px", borderRadius: "12px", border: "none",
              background: "var(--gradient-primary)", color: "white", fontWeight: 600,
              fontSize: "15px", cursor: "pointer",
            }}>
              {loading ? "Creating session..." : "▶ Start Replay"}
            </button>

            {error && <div style={{ marginTop: "12px", color: "var(--color-accent-danger)", fontSize: "13px" }}>{error}</div>}
          </div>
        </div>
      </div>
    );
  }

  // ─── Playing Phase ───
  if (phase === "playing") {
    return (
      <div>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <div>
            <h2 style={{ fontSize: "20px", fontWeight: 700 }}>
              {blindMode ? "🔒 Blind Mode" : `${symbol} — ${timeframe}`}
            </h2>
            {currentCandle && !blindMode && (
              <span style={{ fontSize: "13px", color: "var(--color-text-secondary)" }}>{formatCandleTime(currentCandle.timestamp, true)} · {formatCandleTime(currentCandle.timestamp, false)} UTC</span>
            )}
          </div>
          {currentCandle && (
            <div style={{ fontSize: "28px", fontWeight: 700, fontFamily: "var(--font-mono)",
              color: currentCandle.close >= currentCandle.open ? "#10b981" : "#ef4444" }}>
              <div style={{ fontSize: "12px", color: "var(--color-text-secondary)", fontFamily: "var(--font-sans)" }}>Market price · historical replay</div>
              ${currentCandle.close.toFixed(2)}
            </div>
          )}
        </div>

        {/* Progress Bar */}
        <div style={{ height: "4px", borderRadius: "2px", background: "var(--color-bg-secondary)", marginBottom: "16px" }}>
          <div style={{ height: "100%", borderRadius: "2px", background: "var(--gradient-primary)",
            width: `${progress}%`, transition: "width 0.3s" }} />
        </div>

        <div className="replay-layout" style={{ display: "grid", gridTemplateColumns: "1fr 300px", gap: "16px" }}>
          {/* Chart */}
          <div className="card" style={{ padding: "16px", minHeight: "380px", minWidth: 0 }}>
            {renderChart()}
          </div>

          {/* Right Panel */}
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {/* Playback Controls */}
            <div className="card" style={{ padding: "16px" }}>
              <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--color-text-muted)", marginBottom: "10px",
                textTransform: "uppercase" }}>Controls</div>
              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                <button onClick={() => sendControl(isPaused ? "resume" : "pause")} style={controlBtnStyle}>
                  {isPaused ? "▶ Play" : "⏸ Pause"}
                </button>
                {[1, 5, 25, 100].map(s => (
                  <button key={s} onClick={() => { sendControl("speed", String(s)); setSpeed(s); }}
                    style={{ ...controlBtnStyle,
                      background: speed === s ? "rgba(99,102,241,0.15)" : "var(--color-bg-secondary)",
                      color: speed === s ? "var(--color-accent-primary)" : "var(--color-text-secondary)" }}>
                    {s}x
                  </button>
                ))}
              </div>
              <div style={{ fontSize: "12px", color: "var(--color-text-muted)", marginTop: "8px" }}>
                Bar {currentCandle ? currentCandle.index + 1 : 0} / {currentCandle?.total ?? "?"}
              </div>
              <div style={{ fontSize: "13px", color: "var(--color-text-secondary)", marginTop: "8px", fontVariantNumeric: "tabular-nums" }}>
                Replay timer: {String(Math.floor(elapsedSeconds / 3600)).padStart(2, "0")}:{String(Math.floor(elapsedSeconds / 60) % 60).padStart(2, "0")}:{String(elapsedSeconds % 60).padStart(2, "0")} · {isPaused ? "Paused" : "Playing"}
              </div>
            </div>

            {/* Order Ticket */}
            <div className="card" style={{ padding: "16px" }}>
              <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--color-text-muted)", marginBottom: "10px",
                textTransform: "uppercase" }}>Order Ticket</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginBottom: "10px" }}>
                <div>
                  <label style={{ ...labelStyle, fontSize: "10px" }}>Quantity</label>
                  <input type="number" value={orderQty} onChange={e => setOrderQty(Number(e.target.value))}
                    style={{ ...inputStyle, padding: "6px 8px", fontSize: "13px" }} />
                </div>
                <div>
                  <label style={{ ...labelStyle, fontSize: "10px" }}>Type</label>
                  <select value={orderType} onChange={e => setOrderType(e.target.value)}
                    style={{ ...inputStyle, padding: "6px 8px", fontSize: "13px" }}>
                    <option value="market">Market</option>
                    <option value="limit">Limit</option>
                    <option value="stop">Stop</option>
                  </select>
                </div>
              </div>
              {orderType !== "market" && (
                <div style={{ marginBottom: "10px" }}>
                  <label style={{ ...labelStyle, fontSize: "10px" }}>Price</label>
                  <input type="number" value={orderPrice} onChange={e => setOrderPrice(e.target.value)}
                    style={{ ...inputStyle, padding: "6px 8px", fontSize: "13px" }} placeholder="0.00" step="0.01" />
                </div>
              )}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
                <button onClick={() => placeOrder("buy")} style={{
                  padding: "10px", borderRadius: "8px", border: "none", fontWeight: 600, fontSize: "13px",
                  cursor: "pointer", background: "rgba(16,185,129,0.15)", color: "#10b981",
                }}>BUY</button>
                <button onClick={() => placeOrder("sell")} style={{
                  padding: "10px", borderRadius: "8px", border: "none", fontWeight: 600, fontSize: "13px",
                  cursor: "pointer", background: "rgba(239,68,68,0.15)", color: "#ef4444",
                }}>SELL</button>
              </div>
            </div>

            {/* Position */}
            <div className="card" style={{ padding: "16px" }}>
              <div style={{ fontSize: "12px", fontWeight: 600, color: "var(--color-text-muted)", marginBottom: "8px",
                textTransform: "uppercase" }}>Position</div>
              {Object.keys(positions).length === 0 ? (
                <div style={{ fontSize: "13px", color: "var(--color-text-muted)" }}>No open positions</div>
              ) : (
                Object.entries(positions).map(([sym, pos]) => {
                  const p = pos as { quantity: number; avg_entry: number; unrealized_pnl: number; realized_pnl: number };
                  return (
                    <div key={sym} style={{ fontSize: "13px" }}>
                      <div style={{ fontWeight: 600 }}>{sym}: {p.quantity} shares</div>
                      <div style={{ color: "var(--color-text-muted)" }}>
                        Avg: ${p.avg_entry.toFixed(2)} |{" "}
                        <span style={{ color: p.unrealized_pnl >= 0 ? "#10b981" : "#ef4444" }}>
                          P&L: ${p.unrealized_pnl.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
        <CandleReport candles={candles} candle={selectedCandle || hoveredCandle || currentCandle} symbol={symbol} blindMode={blindMode} selectedCandle={selectedCandle} onSelect={setSelectedCandle} />
        {error && <p role="alert" style={{ color: "var(--color-accent-danger)", marginTop: "12px" }}>{error}</p>}
      </div>
    );
  }

  // ─── Summary Phase ───
  return (
    <div style={{ maxWidth: "600px", margin: "0 auto", textAlign: "center" }}>
      <div className="card" style={{ padding: "40px" }}>
        <div style={{ fontSize: "48px", marginBottom: "16px" }}>🏁</div>
        <h2 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "8px" }}>Session Complete</h2>
        {summary && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", marginTop: "24px", textAlign: "left" }}>
            <StatBox label="Bars Viewed" value={`${summary.bars_viewed} / ${summary.total_bars}`} />
            <StatBox label="Orders Placed" value={String(summary.orders_placed)} />
            <StatBox label="Net P&L" value={`$${summary.net_pnl.toFixed(2)}`}
              color={summary.net_pnl >= 0 ? "#10b981" : "#ef4444"} />
            <StatBox label="Total P&L" value={`$${summary.total_pnl.toFixed(2)}`}
              color={summary.total_pnl >= 0 ? "#10b981" : "#ef4444"} />
          </div>
        )}
        <div style={{ display: "flex", gap: "12px", justifyContent: "center", marginTop: "24px" }}>
          <button onClick={() => { setPhase("config"); setCandles([]); setSummary(null); }} style={{
            padding: "10px 24px", borderRadius: "10px", border: "1px solid var(--color-border)",
            background: "transparent", color: "var(--color-text-primary)", fontWeight: 600, cursor: "pointer",
          }}>New Session</button>
          <button onClick={async () => {
            if (summary) {
              const res = await api.getCritique([], summary);
              setFeedback(res.feedback);
            }
          }} style={{
            padding: "10px 24px", borderRadius: "10px", border: "none",
            background: "var(--gradient-primary)", color: "white", fontWeight: 600, cursor: "pointer",
          }}>🤖 Get AI Feedback</button>
        </div>
        {feedback && (
          <div role="status" style={{ marginTop: "16px", padding: "14px", borderRadius: "10px", background: "var(--color-bg-secondary)", border: "1px solid var(--color-border)", textAlign: "left", fontSize: "14px", lineHeight: 1.6 }}>
            {feedback}
          </div>
        )}
        <CandleReport candles={candles} candle={selectedCandle || currentCandle} symbol={symbol} blindMode={blindMode} selectedCandle={selectedCandle} onSelect={setSelectedCandle} />
        <TradeAnalysisReport trades={trades} summary={summary} symbol={symbol} />
      </div>
    </div>
  );
}

function formatCandleTime(timestamp: string, date: boolean) {
  const parsed = new Date(timestamp);
  if (!Number.isFinite(parsed.getTime())) return "—";
  return date ? parsed.toLocaleDateString("en-GB", { timeZone: "UTC", day: "2-digit", month: "short", year: "numeric" }) : parsed.toLocaleTimeString("en-GB", { timeZone: "UTC", hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function CandleReport({ candles, candle, symbol, blindMode, selectedCandle, onSelect }: { candles: CandleMsg[]; candle: CandleMsg | null; symbol: string; blindMode: boolean; selectedCandle: CandleMsg | null; onSelect: (candle: CandleMsg | null) => void }) {
  if (!candle) return null;
  const body = Math.abs(candle.close - candle.open);
  const range = candle.high - candle.low;
  const change = candle.close - candle.open;
  const first = candles[0];
  const latest = candles[candles.length - 1];
  const replayChange = first?.open ? ((latest.close - first.open) / first.open) * 100 : 0;
  const doji = range === 0 || body / range <= 0.1;
  const direction = doji ? "Doji / indecision" : change > 0 ? "Bullish candle" : "Bearish candle";
  return <section className="card replay-candle-report" aria-labelledby="candle-report-title">
    <div className="replay-report-heading">
      <div><h2 id="candle-report-title" style={{ fontSize: "20px", fontWeight: 700 }}>Candle & stock report</h2><p style={{ color: "var(--color-text-secondary)", fontSize: "13px", marginTop: "6px" }}>{blindMode ? "Hidden symbol" : symbol} · {blindMode ? `Bar ${candle.index + 1}` : `${formatCandleTime(candle.timestamp, true)} · ${formatCandleTime(candle.timestamp, false)} UTC`}</p></div>
      <div><label htmlFor="report-candle" style={labelStyle}>Report candle</label><select id="report-candle" value={selectedCandle?.index ?? "latest"} onChange={event => onSelect(event.target.value === "latest" ? null : candles.find(item => item.index === Number(event.target.value)) || null)} style={inputStyle}><option value="latest">Follow latest / hover</option>{candles.map(item => <option key={item.index} value={item.index}>{blindMode ? `Bar ${item.index + 1}` : `Bar ${item.index + 1} · ${formatCandleTime(item.timestamp, true)} ${formatCandleTime(item.timestamp, false)}`}</option>)}</select></div>
    </div>
    <p style={{ color: "var(--color-text-secondary)", fontSize: "13px", margin: "16px 0" }}>Hover to inspect a candle, or click to keep its report selected. You can also choose a candle from the menu.</p>
    <div className="replay-report-stats">
      <StatBox label="Open" value={`$${candle.open.toFixed(2)}`} /><StatBox label="High" value={`$${candle.high.toFixed(2)}`} /><StatBox label="Low" value={`$${candle.low.toFixed(2)}`} /><StatBox label="Close" value={`$${candle.close.toFixed(2)}`} /><StatBox label="Volume" value={candle.volume.toLocaleString("en-US")} /><StatBox label="Candle change" value={`${change >= 0 ? "+" : ""}${candle.open ? ((change / candle.open) * 100).toFixed(2) : "0.00"}%`} />
    </div>
    <div className="replay-report-details">
      <div><h3 style={{ fontWeight: 600, marginBottom: "8px" }}>{direction}</h3><p>The close is {change > 0 ? "above" : change < 0 ? "below" : "equal to"} the open. The body spans ${body.toFixed(2)} ({range ? ((body / range) * 100).toFixed(0) : "0"}% of the candle range).</p><p>Upper wick: ${(candle.high - Math.max(candle.open, candle.close)).toFixed(2)} · Lower wick: ${(Math.min(candle.open, candle.close) - candle.low).toFixed(2)}.</p><p>{doji ? "A small body indicates limited directional movement within this bar." : "This describes this bar only; a single candle does not establish the next price move."}</p></div>
      <div><h3 style={{ fontWeight: 600, marginBottom: "8px" }}>Stock replay so far</h3><p>{candles.length} bars viewed · Last price ${latest.close.toFixed(2)}</p><p>Change from first open: {replayChange >= 0 ? "+" : ""}{replayChange.toFixed(2)}%</p><p>Range: ${Math.min(...candles.map(item => item.low)).toFixed(2)} – ${Math.max(...candles.map(item => item.high)).toFixed(2)}</p><p>Volume: {candles.reduce((total, item) => total + item.volume, 0).toLocaleString("en-US")}</p></div>
    </div>
  </section>;
}

function TradeAnalysisReport({ trades, summary, symbol }: { trades: TradeRecord[]; summary: SessionSummary | null; symbol: string }) {
  const buys = trades.filter(trade => trade.side.toLowerCase() === "buy");
  const sells = trades.filter(trade => trade.side.toLowerCase() === "sell");
  const averageBuy = buys.length ? buys.reduce((total, trade) => total + trade.price * trade.quantity, 0) / buys.reduce((total, trade) => total + trade.quantity, 0) : 0;
  const averageSell = sells.length ? sells.reduce((total, trade) => total + trade.price * trade.quantity, 0) / sells.reduce((total, trade) => total + trade.quantity, 0) : 0;
  const estimatedPnl = sells.length && buys.length ? (averageSell - averageBuy) * Math.min(buys.reduce((total, trade) => total + trade.quantity, 0), sells.reduce((total, trade) => total + trade.quantity, 0)) : summary?.net_pnl ?? 0;
  const closedTrades = Math.min(buys.length, sells.length);
  const wins = estimatedPnl > 0 ? 1 : 0;
  const losses = estimatedPnl < 0 ? 1 : 0;

  return (
    <section className="replay-analysis card" aria-labelledby="trade-analysis-title">
      <div className="replay-analysis-heading"><div><div className="replay-kicker">POST-SESSION REVIEW</div><h2 id="trade-analysis-title">Trade analysis report</h2><p>{symbol} replay performance after completed executions.</p></div><strong className={estimatedPnl >= 0 ? "replay-profit" : "replay-loss"}>{estimatedPnl >= 0 ? "+" : ""}${estimatedPnl.toFixed(2)}</strong></div>
      <div className="replay-analysis-grid"><div><span>Executions</span><strong>{trades.length}</strong></div><div><span>Closed trades</span><strong>{closedTrades}</strong></div><div><span>Win rate</span><strong>{closedTrades ? `${((wins / closedTrades) * 100).toFixed(0)}%` : "—"}</strong></div><div><span>Wins / losses</span><strong>{wins} / {losses}</strong></div></div>
      <div className="replay-trade-table"><div className="replay-table-head"><span>Side</span><span>Quantity</span><span>Fill price</span><span>Time</span></div>{trades.length ? trades.map((trade, index) => <div className="replay-table-row" key={`${trade.order_id}-${index}`}><span className={trade.side.toLowerCase() === "buy" ? "replay-profit" : "replay-loss"}>{trade.side.toUpperCase()}</span><span>{trade.quantity}</span><span>${trade.price.toFixed(2)}</span><span>{new Date(trade.timestamp).toLocaleString()}</span></div>) : <p className="replay-empty">No executed trades were recorded in this replay.</p>}</div>
    </section>
  );
}

function StatBox({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ padding: "12px", borderRadius: "10px", background: "var(--color-bg-secondary)", border: "1px solid var(--color-border)" }}>
      <div style={{ fontSize: "11px", color: "var(--color-text-muted)", fontWeight: 500, textTransform: "uppercase", marginBottom: "4px" }}>{label}</div>
      <div style={{ fontSize: "18px", fontWeight: 700, fontFamily: "var(--font-mono)", color: color || "var(--color-text-primary)" }}>{value}</div>
    </div>
  );
}

const labelStyle: React.CSSProperties = {
  display: "block", fontSize: "12px", fontWeight: 500, color: "var(--color-text-muted)",
  marginBottom: "4px", textTransform: "uppercase", letterSpacing: "0.04em",
};

const inputStyle: React.CSSProperties = {
  width: "100%", padding: "8px 12px", borderRadius: "8px", fontSize: "14px",
  border: "1px solid var(--color-border)", background: "var(--color-bg-secondary)",
  color: "var(--color-text-primary)", outline: "none",
};

const controlBtnStyle: React.CSSProperties = {
  padding: "6px 14px", borderRadius: "8px", border: "1px solid var(--color-border)",
  background: "var(--color-bg-secondary)", color: "var(--color-text-secondary)",
  fontSize: "12px", fontWeight: 600, cursor: "pointer",
};
