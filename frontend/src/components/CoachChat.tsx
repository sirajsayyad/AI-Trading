"use client";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { request } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import "./coach-chat.css";

export type SimulationContext = { kind: "backtest" | "replay"; symbol: string; metrics: Record<string, number | string | null>; configuration: Record<string, string | number | boolean | null> };

type Message = { role: string; content: string };
type Conversation = { id: string; title: string };
type CoachProps = { courseId?: string; lessonId?: string; lessonTitle?: string; simulationContext?: SimulationContext };
export default function CoachChat(props: CoachProps) {
  const { user } = useAuth();
  if (!user) return <section className="card coach-chat"><h2>AI Coach</h2><p>Sign in to use your private trading coach.</p></section>;
  return <CoachChatSession key={user.id} {...props} userId={user.id} />;
}

function CoachChatSession({ courseId, lessonId, lessonTitle, simulationContext, userId }: CoachProps & { userId: string }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [conversationId, setConversationId] = useState("");
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [owner, setOwner] = useState("");
  const [error, setError] = useState("");
  const [failed, setFailed] = useState("");
  const [model, setModel] = useState("");
  const [notice, setNotice] = useState("");
  const abort = useRef<AbortController | null>(null);
  const log = useRef<HTMLDivElement>(null);
  const active = useRef(true);
  const simulationPayload = simulationContext ? JSON.stringify(simulationContext) : "";
  const scope = lessonId ? `?lesson_id=${encodeURIComponent(lessonId)}` : "";
  useEffect(() => {
    active.current = true;
    let cancelled = false;
    request<Conversation[]>(`/ai-coach/conversations${scope}`).then(async rows => {
      if (cancelled) return;
      setConversations(rows);
      if (rows.length && !simulationPayload) {
        const data = await request<{ messages: Message[] }>(`/ai-coach/conversations/${rows[0].id}`);
        if (!cancelled) { setConversationId(rows[0].id); setMessages(data.messages); }
      } else { setConversationId(""); setMessages([]); }
    }).catch(e => { if (!cancelled) setError(e.message); }).finally(() => { if (!cancelled) { setOwner(userId); setLoading(false); } });
    return () => { cancelled = true; active.current = false; abort.current?.abort(); };
  }, [scope, userId, simulationPayload]);
  useEffect(() => { if (log.current) log.current.scrollTop = log.current.scrollHeight; }, [messages, busy, error]);
  async function send(text = input, retry = false) {
    if (!text.trim() || busy) return;
    const controller = new AbortController(); abort.current = controller;
    setBusy(true); setError(""); setNotice(""); setInput(""); setFailed("");
    if (!retry) setMessages(m => [...m, { role: "user", content: text.trim() }]);
    try {
      const result = await request<{ conversationId: string; answer: string; model: string }>("/ai-coach/chat", { method: "POST", body: { message: text.trim(), conversationId: conversationId || undefined, courseId, lessonId, simulationContext }, signal: controller.signal });
      if (!active.current || controller.signal.aborted) return;
      setMessages(m => [...m, { role: "assistant", content: result.answer }]); setConversationId(result.conversationId); setModel(result.model);
      request<Conversation[]>(`/ai-coach/conversations${scope}`).then(rows => { if (active.current) setConversations(rows); }).catch(() => { if (active.current) setNotice("Response saved. Conversation list will refresh when reopened."); });
    } catch (e) {
      if (!active.current) return;
      if (controller.signal.aborted) setNotice("Generation stopped. The unfinished turn was not saved.");
      else setError((e as Error).message);
      setFailed(text.trim());
    } finally { if (active.current) setBusy(false); }
  }
  async function open(id: string) {
    setError(""); setFailed(""); setNotice("");
    if (!id) { setConversationId(""); setMessages([]); return; }
    setLoading(true);
    try { const data = await request<{ messages: Message[] }>(`/ai-coach/conversations/${id}`); setConversationId(id); setMessages(data.messages); }
    catch (e) { setError((e as Error).message); }
    finally { setLoading(false); }
  }
  async function clear() {
    if (busy) return;
    setLoading(true);
    try {
      if (conversationId) await request(`/ai-coach/conversations/${conversationId}`, { method: "DELETE" });
      setConversations(c => c.filter(row => row.id !== conversationId)); setConversationId(""); setMessages([]); setInput(""); setError(""); setFailed(""); setNotice("Conversation cleared.");
    } catch (e) { setError((e as Error).message); }
    finally { setLoading(false); }
  }
  async function copy(text: string) {
    try {
      if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(text);
      else {
        const focused = document.activeElement as HTMLElement | null;
        const area = document.createElement("textarea"); area.value = text; area.readOnly = true;
        area.style.position = "fixed"; area.style.opacity = "0";
        document.body.appendChild(area); area.select();
        const copied = document.execCommand("copy"); area.remove(); focused?.focus();
        if (!copied) throw new Error("Clipboard unavailable");
      }
      setNotice("Response copied.");
    }
    catch { setError("Clipboard access is unavailable. Select and copy the response text."); }
  }
  if (owner !== userId) return <section className="card coach-chat"><h2>AI Coach</h2><p role="status">Loading your private conversation…</p></section>;
  const suggestions = lessonTitle ? [`Explain ${lessonTitle} with a trading example.`, "How can I practice this lesson in Replay or Backtest?", "What risk-management mistake should I avoid here?"] : ["How does volatility affect stop placement and position size?", "How do I avoid overfitting in a backtest?", "How should I review a simulated trade?"];
  return <section className="card coach-chat" aria-label="AI trading coach">
    <header><div><h2>AI Coach</h2><p>{lessonTitle ? `Lesson: ${lessonTitle}` : "AI trading, Replay & Backtesting"}</p>{simulationContext && <p className="coach-tag">Current {simulationContext.kind} metrics supplied · saved chats retain their original context.</p>}</div><span className="coach-tag">Local AI{model ? ` · ${model}` : ""}</span></header>
    <label className="coach-history-label">Private conversation<select value={conversationId} disabled={busy || loading} onChange={e => void open(e.target.value)}><option value="">New conversation</option>{conversations.map(c => <option key={c.id} value={c.id}>{c.title}</option>)}</select></label>
    <div className="coach-toolbar"><button onClick={() => void open("")} disabled={busy || loading}>New chat</button><button onClick={clear} disabled={busy || loading || !messages.length}>Clear conversation</button></div>
    <div ref={log} className="coach-log" role="log" aria-live="polite" aria-relevant="additions">
      {loading ? <p role="status">Loading conversation…</p> : !messages.length && <div className="coach-empty"><p>Ask a question about trading or the current lesson.</p><div className="coach-suggestions">{suggestions.map(q => <button key={q} onClick={() => setInput(q)}>{q}</button>)}</div></div>}
      {messages.map((m, i) => <article key={i} className={`coach-message ${m.role}`}><strong>{m.role === "user" ? "You" : "Coach"}</strong><div className="coach-markdown"><ReactMarkdown>{m.content}</ReactMarkdown></div>{m.role === "assistant" && <button className="coach-copy" onClick={() => copy(m.content)}>Copy response</button>}</article>)}
      {busy && <p role="status" className="coach-generating">Generating locally… The first response may take longer while the model loads.</p>}
      {error && <div role="alert" className="coach-error">{error}</div>}
      {failed && !busy && <button className="coach-retry" onClick={() => send(failed, true)}>Retry last question</button>}
    </div>
    <p className="coach-notice" role="status">{notice}</p>
    <form onSubmit={e => { e.preventDefault(); if (!failed) void send(); }}><label htmlFor={`coach-input-${lessonId || "general"}`}>Ask {lessonTitle ? "about this trading lesson" : "your trading coach"}</label><textarea id={`coach-input-${lessonId || "general"}`} rows={3} maxLength={4000} value={input} disabled={busy || loading} onChange={e => { setInput(e.target.value); }} onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); if (!busy && !failed) void send(); } }} placeholder="Enter to send · Shift+Enter for a new line" /><div className="coach-send-row"><span>{input.length}/4000</span>{busy ? <button type="button" className="coach-send" onClick={() => abort.current?.abort()}>Stop generation</button> : <button className="coach-send" disabled={!input.trim() || loading || !!failed}>Send</button>}</div></form>
    {failed && <button className="coach-copy" onClick={() => { setMessages(m => m.slice(0, -1)); setFailed(""); setError(""); setInput(failed); }}>Edit failed question</button>}
    <p className="coach-disclaimer">AI-generated education, not financial advice. Verify explanations and calculations. Examples and historical simulations do not guarantee future results. The coach cannot place orders.</p>
  </section>;
}
