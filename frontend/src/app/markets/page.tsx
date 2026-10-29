"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AreaSeries, CandlestickSeries, ColorType, createChart, HistogramSeries, LineSeries, type IChartApi, type ISeriesApi, type SeriesType, type Time } from "lightweight-charts";
import { api, getMarketWsUrl, type OrderPreview, type PaperPortfolio } from "@/lib/api";

type Candle = Awaited<ReturnType<typeof api.getLiveCandles>>[number] & { simulated?: boolean };
type Quote = Awaited<ReturnType<typeof api.getLiveQuote>>;
type ChartMode = "candles" | "line" | "area";
type OrderSide = "buy" | "sell";
type OrderType = "market" | "limit";
type Position = PaperPortfolio["positions"][number];
type Order = PaperPortfolio["orders"][number];
type Indicator = "sma" | "ema" | "bb" | "rsi" | "macd" | "volume";

const formatMoney = (value: number) => value.toLocaleString("en-US", { maximumFractionDigits: 2 });

const symbols = ["AAPL", "TSLA", "NVDA", "MSFT", "AMZN"];
const timeframes = ["1m", "5m", "15m", "1h", "4h", "1D"];
const indicators: Array<{ key: Indicator; label: string }> = [
  { key: "sma", label: "SMA 20" }, { key: "ema", label: "EMA 20" }, { key: "bb", label: "Bollinger" },
  { key: "rsi", label: "RSI" }, { key: "macd", label: "MACD" }, { key: "volume", label: "Volume" },
];

function seedCandles(symbol: string, timeframe: string): Candle[] {
  let price = symbol.includes("BTC") ? 63250 : symbol.includes("EUR") ? 1.084 : 190;
  const step = timeframeSeconds(timeframe);
  return Array.from({ length: 100 }, (_, index) => {
    const drift = Math.sin(index / 8) * 0.004 + (Math.random() - 0.5) * 0.012;
    const open = price;
    const close = Math.max(0.01, open * (1 + drift));
    const high = Math.max(open, close) * (1 + Math.random() * 0.006);
    const low = Math.min(open, close) * (1 - Math.random() * 0.006);
    price = close;
    return { symbol, timeframe, timestamp: new Date(Date.now() - (99 - index) * step * 1000).toISOString(), open, high, low, close, volume: Math.round(800 + Math.random() * 2400), simulated: true, provider: "demo" };
  });
}

function timeframeSeconds(value: string) {
  const units: Record<string, number> = { m: 60, h: 3600, D: 86400 };
  const unit = value.at(-1) || "m";
  return Number(value.slice(0, -1)) * (units[unit] || 60);
}

// lightweight-charts requires unique, strictly ascending timestamps. Live quote
// polling can update the current candle more than once within the same second,
// so keep the newest value for each chart bucket before sending it to the chart.
function normalizeChartCandles(candles: Candle[]) {
  const byTime = new Map<number, Candle>();
  candles.forEach((candle) => {
    const time = Math.floor(new Date(candle.timestamp).getTime() / 1000);
    if (Number.isFinite(time) && time > 0) byTime.set(time, candle);
  });
  return [...byTime.entries()].sort(([left], [right]) => left - right).map(([time, candle]) => ({ time, candle }));
}

function nextCandle(previous: Candle, timeframe: string): Candle {
  const drift = Math.sin(Date.now() / 17000) * 0.002 + (Math.random() - 0.5) * 0.009;
  const open = previous.close;
  const close = Math.max(0.01, open * (1 + drift));
  return { ...previous, timestamp: new Date(Date.now()).toISOString(), open, close, high: Math.max(open, close) * (1 + Math.random() * 0.004), low: Math.min(open, close) * (1 - Math.random() * 0.004), volume: Math.round(700 + Math.random() * 2800), timeframe, simulated: true };
}

function seriesValues(candles: Candle[], kind: "sma" | "ema" | "bb") {
  const values: Array<{ time: Time; value: number }> = [];
  let ema = candles[0]?.close || 0;
  candles.forEach((candle, index) => {
    const window = candles.slice(Math.max(0, index - 19), index + 1);
    const average = window.reduce((sum, item) => sum + item.close, 0) / window.length;
    ema = index === 0 ? candle.close : candle.close * 0.095 + ema * 0.905;
    const value = kind === "sma" ? average : kind === "ema" ? ema : average + Math.sqrt(window.reduce((sum, item) => sum + (item.close - average) ** 2, 0) / window.length) * 2;
    values.push({ time: Math.floor(new Date(candle.timestamp).getTime() / 1000) as Time, value });
  });
  return values;
}

function TradingChart({ candles, mode, activeIndicators, onPrice, onCandle }: { candles: Candle[]; mode: ChartMode; activeIndicators: Set<Indicator>; onPrice: (price: number) => void; onCandle: (candle: Candle | null) => void }) {
  const elementRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const mainSeriesRef = useRef<ISeriesApi<SeriesType> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<SeriesType> | null>(null);
  const indicatorSeriesRef = useRef<ISeriesApi<SeriesType>[]>([]);
  const candlesRef = useRef(candles);
  const onPriceRef = useRef(onPrice);
  const onCandleRef = useRef(onCandle);
  useEffect(() => { candlesRef.current = candles; }, [candles]);
  useEffect(() => { onPriceRef.current = onPrice; }, [onPrice]);
  useEffect(() => { onCandleRef.current = onCandle; }, [onCandle]);

  useEffect(() => {
    if (!elementRef.current) return;
    const chart = createChart(elementRef.current, { layout: { background: { type: ColorType.Solid, color: "#061017" }, textColor: "#71929c" }, grid: { vertLines: { color: "rgba(65,145,159,.10)" }, horzLines: { color: "rgba(65,145,159,.14)" } }, rightPriceScale: { borderColor: "#153741" }, timeScale: { borderColor: "#153741", timeVisible: true }, crosshair: { mode: 0 }, autoSize: true });
    const main = mode === "candles" ? chart.addSeries(CandlestickSeries, { upColor: "#00e5b0", downColor: "#ff3158", borderVisible: false, wickUpColor: "#00e5b0", wickDownColor: "#ff3158" }) : mode === "area" ? chart.addSeries(AreaSeries, { lineColor: "#00d9e8", topColor: "rgba(0,217,232,.25)", bottomColor: "rgba(0,217,232,.01)", lineWidth: 2 }) : chart.addSeries(LineSeries, { color: "#00d9e8", lineWidth: 2 });
    chartRef.current = chart;
    mainSeriesRef.current = main;
    volumeSeriesRef.current = activeIndicators.has("volume") ? chart.addSeries(HistogramSeries, { color: "rgba(0,217,232,.28)", priceFormat: { type: "volume" }, priceScaleId: "volume" }) : null;
    if (volumeSeriesRef.current) chart.priceScale("volume").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
    indicatorSeriesRef.current = (["sma", "ema", "bb"] as const).filter((kind) => activeIndicators.has(kind)).map((kind) => chart.addSeries(LineSeries, { color: kind === "sma" ? "#f4c95d" : kind === "ema" ? "#a78bfa" : "#ff9f68", lineWidth: 1 }));
    chart.subscribeCrosshairMove((param) => {
      const point = param.seriesData.get(main);
      const price = point && "close" in point ? point.close : point && "value" in point ? point.value : undefined;
      if (price) onPriceRef.current(price);
      const timestamp = point?.time;
      const candle = timestamp ? candlesRef.current.find((item) => Math.floor(new Date(item.timestamp).getTime() / 1000) === Number(timestamp)) : undefined;
      onCandleRef.current(candle || null);
    });
    return () => { chart.remove(); chartRef.current = null; mainSeriesRef.current = null; volumeSeriesRef.current = null; indicatorSeriesRef.current = []; };
  }, [mode, activeIndicators]);

  useEffect(() => {
    const chart = chartRef.current;
    const main = mainSeriesRef.current;
    const currentCandles = candlesRef.current;
    if (!chart || !main || !currentCandles.length) return;
    const normalized = normalizeChartCandles(currentCandles);
    if (!normalized.length) return;
    const chartCandles = normalized.map(({ time, candle }) => ({ time: time as Time, candle }));
    const data = chartCandles.map(({ time, candle }) => ({ time, open: candle.open, high: candle.high, low: candle.low, close: candle.close }));
    const lineData = chartCandles.map(({ time, candle }) => ({ time, value: candle.close }));
    main.setData((mode === "candles" ? data : lineData) as never);
    volumeSeriesRef.current?.setData(chartCandles.map(({ time, candle }) => ({ time, value: candle.volume, color: candle.close >= candle.open ? "rgba(0,229,176,.42)" : "rgba(255,49,88,.42)" })) as never);
    (["sma", "ema", "bb"] as const).filter((kind) => activeIndicators.has(kind)).forEach((kind, index) => indicatorSeriesRef.current[index]?.setData(seriesValues(chartCandles.map(({ candle }) => candle), kind) as never));
  }, [candles, mode, activeIndicators]);

  return <div ref={elementRef} className="tv-chart" aria-label="Interactive market chart" />;
}

export default function MarketsPage() {
  const [symbol, setSymbol] = useState("AAPL");
  const [timeframe, setTimeframe] = useState("1m");
  const [chartMode, setChartMode] = useState<ChartMode>("candles");
  const [candles, setCandles] = useState<Candle[]>([]);
  const [activeIndicators, setActiveIndicators] = useState<Set<Indicator>>(new Set(["volume"]));
  const [orderSide, setOrderSide] = useState<OrderSide>("buy");
  const [orderType, setOrderType] = useState<OrderType>("market");
  const [quantity, setQuantity] = useState("10");
  const [limitPrice, setLimitPrice] = useState("");
  const [stopPrice, setStopPrice] = useState("");
  const [targetPrice, setTargetPrice] = useState("");
  const [orderPreview, setOrderPreview] = useState<OrderPreview | null>(null);
  const [orderError, setOrderError] = useState("");
  const [positions, setPositions] = useState<Position[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [balance, setBalance] = useState(100000);
  const [marketValue, setMarketValue] = useState(0);
  const [activeTab, setActiveTab] = useState<"positions" | "orders" | "history">("positions");
  const [hoverPrice, setHoverPrice] = useState<number | null>(null);
  const [selectedCandle, setSelectedCandle] = useState<Candle | null>(null);
  const [status, setStatus] = useState("SIMULATION MODE");
  const [quote, setQuote] = useState<Quote | null>(null);

  const current = candles.at(-1);
  const visibleCandles = candles;
  const liveQuote = quote?.symbol === symbol ? quote : null;
  const hasLiveQuote = Boolean(liveQuote);
  const price = hoverPrice ?? liveQuote?.price ?? current?.close ?? 0;
  const change = liveQuote?.change ?? (current ? current.close - current.open : 0);
  const changePercent = liveQuote?.percent_change ?? (current ? (change / current.open) * 100 : 0);
  const unrealized = positions.reduce((sum, position) => sum + position.unrealized_pnl, 0);
  const equity = balance + marketValue;
  const analysis = useMemo(() => {
    const recent = candles.slice(-20);
    const first = recent[0]?.close || price || 1;
    const trend = price > first * 1.005 ? "Bullish" : price < first * 0.995 ? "Bearish" : "Sideways";
    const high = recent.length ? Math.max(...recent.map((c) => c.high)) : 0;
    const low = recent.length ? Math.min(...recent.map((c) => c.low)) : 0;
    const volatility = recent.length ? recent.reduce((sum, c) => sum + ((c.high - c.low) / c.open) * 100, 0) / recent.length : 0;
    return { trend, high, low, volatility, momentum: ((price - first) / first) * 100 };
  }, [candles, price]);

  const loadPortfolio = async () => {
    try {
      const portfolio = await api.getPaperPortfolio();
      setBalance(portfolio.cash);
      setMarketValue(portfolio.market_value);
      setPositions(portfolio.positions);
      setOrders(portfolio.orders);
    } catch { /* signed-out users can still inspect market data */ }
  };
  useEffect(() => {
    let active = true;
    api.getPaperPortfolio().then(portfolio => {
      if (!active) return;
      setBalance(portfolio.cash);
      setMarketValue(portfolio.market_value);
      setPositions(portfolio.positions);
      setOrders(portfolio.orders);
    }).catch(() => { /* signed-out users can still inspect market data */ });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try { const live = await api.getLiveCandles(symbol, timeframe, 100); if (!cancelled && live.length) { setCandles(live.map((c) => ({ ...c, simulated: c.provider === "demo" }))); setStatus(live.some(c => c.provider === "demo") ? "DEMO DATA · SIMULATED PRICES" : "PROVIDER CANDLES"); return; } } catch { /* simulator is the safe fallback */ }
      if (!cancelled) { setCandles(seedCandles(symbol, timeframe)); setStatus("SIMULATION MODE"); }
    };
    load();
    return () => { cancelled = true; };
  }, [symbol, timeframe]);

  useEffect(() => {
    let cancelled = false;

    const refreshQuote = async () => {
      try {
        const nextQuote = await api.getLiveQuote(symbol);
        if (cancelled) return;
        setQuote(nextQuote);
        setStatus(nextQuote.is_market_open ? "LIVE · MARKET OPEN" : "LIVE · MARKET CLOSED");
        setCandles((items) => {
          const last = items.at(-1);
          if (!last || items.some(c => c.simulated || c.provider === "demo")) return items;
          return [...items.slice(0, -1), { ...last, close: nextQuote.price, high: Math.max(last.high, nextQuote.price), low: Math.min(last.low, nextQuote.price), simulated: false }];
        });
      } catch {
        if (!cancelled) setStatus("LIVE QUOTE UNAVAILABLE");
      }
    };

    refreshQuote();
    const timer = window.setInterval(refreshQuote, 15_000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [symbol]);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let timer: number | undefined;
    let stopped = false;
    let delay = 1000;
    const connect = () => {
      socket = new WebSocket(getMarketWsUrl(symbol));
      socket.onopen = () => { delay = 1000; setStatus("LIVE STREAM CONNECTED"); };
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === "quote") setQuote(message.data as Quote);
        if (message.type === "stale") setStatus("STALE DATA · RECONNECTING");
      };
      socket.onclose = () => {
        if (stopped) return;
        setStatus("REST POLLING · RECONNECTING");
        timer = window.setTimeout(connect, delay);
        delay = Math.min(delay * 2, 30000);
      };
    };
    connect();
    return () => { stopped = true; if (timer) window.clearTimeout(timer); socket?.close(); };
  }, [symbol]);

  useEffect(() => {
    if (hasLiveQuote) return;
    const timer = window.setInterval(() => setCandles((items) => { if (items.length && !items.some(c => c.simulated || c.provider === "demo")) return items; const next = nextCandle(items.at(-1) || seedCandles(symbol, timeframe)[0], timeframe); return [...items.slice(-99), next]; }), 1000);
    return () => window.clearInterval(timer);
  }, [symbol, timeframe, hasLiveQuote]);

  const toggleIndicator = (key: Indicator) => setActiveIndicators((currentSet) => { const next = new Set(currentSet); if (next.has(key)) next.delete(key); else next.add(key); return next; });
  const executeOrder = async () => {
    const qty = Number(quantity);
    if (!Number.isFinite(qty) || qty <= 0) return;
    setOrderError("");
    const payload = {
      symbol, side: orderSide, order_type: orderType, quantity: qty,
      ...(orderType === "limit" ? { limit_price: Number(limitPrice) } : {}),
      ...(stopPrice ? { stop_price: Number(stopPrice) } : {}),
      ...(targetPrice ? { take_profit_price: Number(targetPrice) } : {}),
      idempotency_key: Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, "0")).join(""),
    } as const;
    try {
      const preview = await api.previewPaperOrder(payload);
      setOrderPreview(preview);
      if (!preview.allowed) return;
      const confirmed = window.confirm(`Confirm PAPER ${orderSide.toUpperCase()} ${qty} ${symbol}?\nEstimated maximum loss: $${preview.risk_amount.toFixed(2)}\nReward:risk: ${preview.reward_risk_ratio.toFixed(2)}:1`);
      if (!confirmed) return;
      const result = await api.submitPaperOrder(payload);
      if (result.status === "rejected") setOrderError(result.errors?.join(". ") || "Order rejected");
      await loadPortfolio();
    } catch (reason) {
      setOrderError(reason instanceof Error ? reason.message : "Paper order failed");
    }
  };
  const closePosition = async (position: Position) => {
    try {
      await api.submitPaperOrder({ symbol: position.symbol, side: "sell", order_type: "market", quantity: position.quantity, idempotency_key: Array.from(crypto.getRandomValues(new Uint8Array(16)), byte => byte.toString(16).padStart(2, "0")).join("") });
      await loadPortfolio();
    } catch (reason) { setOrderError(reason instanceof Error ? reason.message : "Could not close position"); }
  };
  const resetAccount = () => window.alert("Paper account reset is intentionally disabled to preserve the audit history.");

  return <div className="terminal-screen">
    <header className="terminal-heading"><div><div className="eyebrow">AI TRADING TRAINER</div><h1>Market workspace</h1><p>Practice decisions with live data or a realistic paper-trading simulator.</p></div><div className="terminal-status"><span className="status-dot" />{candles.some(c => c.simulated || c.provider === "demo") ? "DEMO DATA · SIMULATED PRICES" : liveQuote ? `${liveQuote.provider.toUpperCase()} · LATEST QUOTE` : candles.length ? "HISTORICAL PROVIDER CANDLES" : status}<button onClick={resetAccount}>RESET PAPER ACCOUNT</button></div></header>
    <div className="account-strip"><div><span>Equity</span><strong>${formatMoney(equity)}</strong></div><div><span>Available funds</span><strong>${formatMoney(balance)}</strong></div><div><span>Open P&amp;L</span><strong className={unrealized >= 0 ? "up" : "down"}>{unrealized >= 0 ? "+" : ""}${unrealized.toFixed(2)}</strong></div><div><span>Positions</span><strong>{positions.length}</strong></div></div>
    <div className="trading-layout">
      <aside className="watchlist-panel terminal-panel"><div className="panel-heading"><h2>Markets</h2><span>US STOCKS</span></div><input className="terminal-input" placeholder="Enter symbol + Return" aria-label="Stock symbol" onKeyDown={(event) => { if (event.key === "Enter") setSymbol(event.currentTarget.value.trim().toUpperCase()); }} />{symbols.map((item) => <button className={`watch-row ${symbol === item ? "selected" : ""}`} key={item} onClick={() => setSymbol(item)}><span><strong>{item}</strong><small>US EQUITY</small></span><b className={item === symbol ? "up" : "neutral"}>{item === symbol ? `$${price.toFixed(2)}` : "—"}</b></button>)}</aside>
      <main className="chart-panel terminal-panel"><div className="chart-toolbar"><div><strong>{symbol}</strong><span className="live-price">${price.toFixed(2)}</span><span className={change >= 0 ? "up" : "down"}>{change >= 0 ? "+" : ""}{change.toFixed(2)} ({changePercent.toFixed(2)}%)</span></div><div className="toolbar-controls"><select value={timeframe} onChange={(event) => setTimeframe(event.target.value)} aria-label="Timeframe">{timeframes.map((item) => <option key={item}>{item}</option>)}</select><select value={chartMode} onChange={(event) => setChartMode(event.target.value as ChartMode)} aria-label="Chart type"><option value="candles">Candles</option><option value="line">Line</option><option value="area">Area</option></select></div></div><TradingChart candles={visibleCandles} mode={chartMode} activeIndicators={activeIndicators} onPrice={setHoverPrice} onCandle={setSelectedCandle} /><div className="indicator-row">{indicators.map((item) => <button key={item.key} className={activeIndicators.has(item.key) ? "active" : ""} onClick={() => toggleIndicator(item.key)}>{item.label}</button>)}</div><div className="candle-analysis"><div><span>Selected candle</span><strong>{selectedCandle ? new Date(selectedCandle.timestamp).toLocaleDateString() : "Move over a candle"}</strong><small>{selectedCandle ? new Date(selectedCandle.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Hover the chart to inspect price action"}</small></div><div><span>Share price</span><strong>${(selectedCandle?.close ?? price).toFixed(2)}</strong><small className={selectedCandle && selectedCandle.close >= selectedCandle.open ? "up" : "down"}>{selectedCandle ? `${selectedCandle.close >= selectedCandle.open ? "Bullish" : "Bearish"} candle` : hasLiveQuote ? "Provider quote" : "Simulated price"}</small></div><div><span>OHLC</span><strong>{selectedCandle ? `$${selectedCandle.open.toFixed(2)} / $${selectedCandle.high.toFixed(2)}` : "—"}</strong><small>{selectedCandle ? `Low $${selectedCandle.low.toFixed(2)} · Vol ${selectedCandle.volume.toLocaleString()}` : "Select a candle"}</small></div></div></main>
      <aside className="order-panel terminal-panel"><div className="panel-heading"><h2>Paper order</h2><span>SIMULATED</span></div><div className="segmented"><button className={orderSide === "buy" ? "active long" : ""} onClick={() => setOrderSide("buy")}>BUY</button><button className={orderSide === "sell" ? "active short" : ""} onClick={() => setOrderSide("sell")}>SELL TO CLOSE</button></div><div className="segmented"><button className={orderType === "market" ? "active" : ""} onClick={() => setOrderType("market")}>MARKET</button><button className={orderType === "limit" ? "active" : ""} onClick={() => setOrderType("limit")}>LIMIT</button></div><label className="field-label">Quantity<input className="terminal-input" type="number" min="1" value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label>{orderType === "limit" && <label className="field-label">Limit price<input className="terminal-input" type="number" min="0.01" value={limitPrice} placeholder={price.toFixed(2)} onChange={(event) => setLimitPrice(event.target.value)} /></label>}<label className="field-label">Stop-loss<input className="terminal-input" type="number" min="0.01" value={stopPrice} placeholder="Required for new positions" onChange={(event) => setStopPrice(event.target.value)} /></label><label className="field-label">Take-profit<input className="terminal-input" type="number" min="0.01" value={targetPrice} placeholder="Target price" onChange={(event) => setTargetPrice(event.target.value)} /></label><button className={`execute-button ${orderSide === "buy" ? "long" : "short"}`} onClick={executeOrder}>{orderSide === "buy" ? "PREVIEW PAPER BUY" : "PREVIEW PAPER SELL"}</button>{orderError && <p className="order-errors" role="alert">{orderError}</p>}{orderPreview && <div className={`order-preview ${orderPreview.allowed ? "valid" : "invalid"}`}><strong>{orderPreview.allowed ? "Risk check passed" : "Order blocked"}</strong><span>Risk ${orderPreview.risk_amount.toFixed(2)} ({orderPreview.risk_percent.toFixed(2)}%)</span><span>Reward:risk {orderPreview.reward_risk_ratio.toFixed(2)}:1</span><span>Fees + slippage ${(orderPreview.estimated_commission + orderPreview.estimated_slippage).toFixed(2)}</span>{orderPreview.errors.map((item) => <small key={item}>{item}</small>)}</div>}<div className="risk-note">Paper trading only. Educational use only—not financial advice.</div><div className="analysis-box"><div className="panel-heading"><h2>Market statistics</h2><span>EDUCATIONAL</span></div><strong className={analysis.trend === "Bullish" ? "up" : analysis.trend === "Bearish" ? "down" : "neutral"}>{analysis.trend} trend</strong><p>Momentum {analysis.momentum >= 0 ? "+" : ""}{analysis.momentum.toFixed(2)}% with {analysis.volatility.toFixed(2)}% average candle range.</p><div className="levels"><span>Resistance <b>${analysis.high.toFixed(2)}</b></span><span>Support <b>${analysis.low.toFixed(2)}</b></span></div></div></aside>
    </div>
    <section className="bottom-panel terminal-panel"><div className="bottom-tabs">{(["positions", "orders", "history"] as const).map((tab) => <button key={tab} className={activeTab === tab ? "active" : ""} onClick={() => setActiveTab(tab)}>{tab.toUpperCase()} {tab === "positions" ? `(${positions.length})` : tab === "orders" ? `(${orders.length})` : ""}</button>)}</div>{activeTab === "positions" && <div className="table-wrap"><table className="terminal-table"><thead><tr><th>Symbol</th><th>Quantity</th><th>Entry</th><th>Mark</th><th>Unrealized P&amp;L</th><th /></tr></thead><tbody>{positions.length ? positions.map((position) => <tr key={position.id}><td>{position.symbol}</td><td>{position.quantity}</td><td>${position.avg_entry_price.toFixed(2)}</td><td>${position.mark_price.toFixed(2)}</td><td className={position.unrealized_pnl >= 0 ? "up" : "down"}>{position.unrealized_pnl >= 0 ? "+" : ""}${position.unrealized_pnl.toFixed(2)}</td><td><button className="table-action" onClick={() => closePosition(position)}>CLOSE</button></td></tr>) : <tr><td colSpan={6} className="empty-row">No open positions. Place a paper order to begin.</td></tr>}</tbody></table></div>}{activeTab === "orders" && <div className="table-wrap"><table className="terminal-table"><thead><tr><th>Symbol</th><th>Side</th><th>Quantity</th><th>Fill</th><th>Status</th></tr></thead><tbody>{orders.length ? orders.map((order) => <tr key={order.id}><td>{order.symbol}</td><td className={order.side === "buy" ? "up" : "down"}>{order.side.toUpperCase()}</td><td>{order.quantity}</td><td>{order.fill_price ? `$${order.fill_price.toFixed(2)}` : "—"}</td><td>{order.status}</td></tr>) : <tr><td colSpan={5} className="empty-row">No orders yet.</td></tr>}</tbody></table></div>}{activeTab === "history" && <div className="history-copy">Orders, fills, fees, and risk checks are persisted to your authenticated paper account.</div>}</section>
  </div>;
}
