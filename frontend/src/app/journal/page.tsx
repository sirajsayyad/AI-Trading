"use client";

import { FormEvent, useEffect, useState } from "react";

import ProtectedRoute from "@/components/ProtectedRoute";
import { api, type JournalEntry, type JournalInput } from "@/lib/api";

const empty: JournalInput = {
  symbol: "AAPL", strategy: "", setup: "", entry_reason: "", exit_reason: "",
  confidence: 5, emotion_before: "neutral", emotion_during: "neutral",
  emotion_after: "neutral", mistakes: "", lessons_learned: "", review: "", tags: [],
};

export default function JournalPage() {
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [form, setForm] = useState<JournalInput>(empty);
  const [message, setMessage] = useState("");
  const [page, setPage] = useState(1);
  const [busy, setBusy] = useState(false);
  const load = () => api.getJournal(page).then(setEntries).catch(() => setMessage("Could not load journal."));
  useEffect(() => {
    let active = true;
    async function fetchPage() {
      setBusy(true);
      try { const result = await api.getJournal(page); if (active) { setEntries(result); setMessage(""); } }
      catch { if (active) { setEntries([]); setMessage("Could not load journal. Try changing pages or refresh."); } }
      finally { if (active) setBusy(false); }
    }
    void fetchPage();
    return () => { active = false; };
  }, [page]);

  const submit = async (event: FormEvent) => {
    event.preventDefault(); setMessage("");
    try { await api.createJournal(form); setForm(empty); setMessage("Journal entry saved."); load(); }
    catch (reason) { setMessage(reason instanceof Error ? reason.message : "Could not save journal."); }
  };
  const remove = async (id: string) => {
    if (!window.confirm("Delete this journal entry?")) return;
    await api.deleteJournal(id); load();
  };

  return <ProtectedRoute><div className="journal-page"><header className="page-heading"><div><div className="eyebrow">POST-TRADE REVIEW</div><h1>Trading journal</h1><p>Capture the decision, emotion, mistake, and lesson behind each paper trade.</p></div></header><div className="journal-layout"><form className="terminal-panel journal-form" onSubmit={submit}><div className="panel-heading"><h2>New review</h2><span>REQUIRED FIELDS</span></div><div className="journal-grid"><label>Symbol<input required value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })} /></label><label>Strategy<input value={form.strategy} onChange={(e) => setForm({ ...form, strategy: e.target.value })} /></label><label>Setup<input value={form.setup} onChange={(e) => setForm({ ...form, setup: e.target.value })} /></label><label>Confidence: {form.confidence}<input type="range" min="1" max="10" value={form.confidence} onChange={(e) => setForm({ ...form, confidence: Number(e.target.value) })} /></label></div><label>Entry reason<textarea value={form.entry_reason} onChange={(e) => setForm({ ...form, entry_reason: e.target.value })} /></label><label>Exit reason<textarea value={form.exit_reason} onChange={(e) => setForm({ ...form, exit_reason: e.target.value })} /></label><label>Mistakes<textarea value={form.mistakes} onChange={(e) => setForm({ ...form, mistakes: e.target.value })} /></label><label>Lesson learned<textarea value={form.lessons_learned} onChange={(e) => setForm({ ...form, lessons_learned: e.target.value })} /></label><button className="primary-button" type="submit">Save review</button>{message && <p role="status" className="form-message">{message}</p>}</form><section className="journal-list"><div className="panel-heading"><h2>Recent entries</h2><span>{entries.length} ENTRIES</span></div>{entries.length ? entries.map((entry) => <article className="terminal-panel journal-card" key={entry.id}><div><strong>{entry.symbol}</strong><span>{entry.strategy || "Unspecified strategy"}</span></div><time>{new Date(entry.created_at).toLocaleDateString()}</time><p>{entry.lessons_learned || entry.review || "No lesson recorded."}</p><button onClick={() => remove(entry.id)}>Delete</button></article>) : <div className="terminal-panel empty-state">{busy ? "Loading journal?" : "No entries on this page. Close a paper trade, then record what you learned."}</div>}<nav className="journal-pagination" aria-label="Journal pages"><button disabled={busy || page === 1} onClick={() => setPage(p => p - 1)}>Previous</button><span role="status">Page {page}</span><button disabled={busy || entries.length < 20} onClick={() => setPage(p => p + 1)}>Next</button></nav></section></div></div></ProtectedRoute>;
}
