"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";
import LiveMarketTicker from "@/components/LiveMarketTicker";

interface Course {
  id: string;
  title: string;
  description: string;
  difficulty: string;
}

export default function TrainingPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [behaviorFlags, setBehaviorFlags] = useState<Array<Record<string, unknown>>>([]);

  useEffect(() => {
    const loadCourses = async () => {
      try {
        const data = await api.getCourses();
        setCourses(data);
      } catch {
        setCourses(sampleCourses);
      } finally {
        setLoading(false);
      }
    };
    loadCourses();
  }, []);

  const sendMessage = async () => {
    if (!chatInput.trim()) return;
    const msg = chatInput;
    setChatInput("");
    setChatMessages(prev => [...prev, { role: "user", content: msg }]);
    setChatLoading(true);
    try {
      const res = await api.askCoach(msg, undefined, chatMessages);
      setChatMessages(prev => [...prev, { role: "assistant", content: res.answer }]);
    } catch {
      setChatMessages(prev => [...prev, { role: "assistant", content: "Sorry, I couldn't process that. Please try again." }]);
    } finally {
      setChatLoading(false);
    }
  };

  const analyzeBehavior = async () => {
    try {
      const res = await api.analyzeBehavior(sampleTrades, 100000);
      setBehaviorFlags(res.flags as Array<Record<string, unknown>>);
    } catch {
      setBehaviorFlags([]);
    }
  };

  const difficultyColor = (d: string) => {
    switch (d) {
      case "beginner": return "#10b981";
      case "intermediate": return "#f59e0b";
      case "advanced": return "#ef4444";
      default: return "#6366f1";
    }
  };

  return (
    <div>
      <div className="page-heading" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "32px" }}>
        <div>
          <h1 style={{ fontSize: "28px", fontWeight: 700, marginBottom: "8px" }}>AI Training</h1>
          <p style={{ color: "var(--color-text-secondary)", fontSize: "15px" }}>
            Structured courses with AI coaching and hands-on replay scenarios.
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
          {/* Course Catalog */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "16px", marginBottom: "32px" }}>
            {loading ? [1, 2, 3].map((item) => (
              <div key={item} className="card" aria-label="Loading course" style={{ minHeight: "180px" }}>
                <div className="skeleton skeleton-short" />
                <div className="skeleton skeleton-title" />
                <div className="skeleton skeleton-line" />
                <div className="skeleton skeleton-line" />
              </div>
            )) : (courses.length > 0 ? courses : sampleCourses).map((course, i) => (
              <div key={course.id} className="card" style={{ cursor: "pointer" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
                  <span style={{
                    padding: "3px 10px", borderRadius: "6px", fontSize: "11px", fontWeight: 600,
                    textTransform: "uppercase", letterSpacing: "0.05em",
                    background: `${difficultyColor(course.difficulty)}15`,
                    color: difficultyColor(course.difficulty),
                  }}>
                    {course.difficulty}
                  </span>
                  <span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>
                    {3 - i} modules
                  </span>
                </div>
                <h3 style={{ fontSize: "16px", fontWeight: 600, marginBottom: "8px" }}>{course.title}</h3>
                <p style={{ fontSize: "13px", color: "var(--color-text-secondary)", lineHeight: 1.6, marginBottom: "16px" }}>
                  {course.description}
                </p>
                <div style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "8px 0", borderTop: "1px solid var(--color-border)",
                }}>
                  <div style={{ height: "4px", flex: 1, borderRadius: "2px", background: "var(--color-bg-secondary)", marginRight: "12px" }}>
                    <div style={{ height: "100%", borderRadius: "2px", background: "var(--gradient-primary)", width: "0%" }} />
                  </div>
                  <span style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>0%</span>
                </div>
              </div>
            ))}
          </div>

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

        {/* AI Coach Chat Panel */}
        {chatOpen && (
          <div className="card" style={{
            padding: 0, display: "flex", flexDirection: "column", height: "calc(100vh - 140px)",
            position: "sticky", top: "80px", overflow: "hidden",
          }}>
            <div style={{
              padding: "16px", borderBottom: "1px solid var(--color-border)",
              display: "flex", alignItems: "center", gap: "10px",
            }}>
              <div style={{
                width: "32px", height: "32px", borderRadius: "8px", background: "var(--gradient-primary)",
                display: "flex", alignItems: "center", justifyContent: "center", fontSize: "16px",
              }}>🤖</div>
              <div>
                <div style={{ fontSize: "14px", fontWeight: 600 }}>AI Trading Coach</div>
                <div style={{ fontSize: "11px", color: "var(--color-text-muted)" }}>Ask anything about trading</div>
              </div>
            </div>

            <div style={{ flex: 1, overflow: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: "12px" }}>
              {chatMessages.length === 0 && (
                <div style={{ textAlign: "center", padding: "32px 16px", color: "var(--color-text-muted)", fontSize: "13px" }}>
                  Ask the AI coach about trading strategies, risk management, or get feedback on your trades.
                </div>
              )}
              {chatMessages.map((msg, i) => (
                <div key={i} style={{
                  alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                  maxWidth: "85%", padding: "10px 14px", borderRadius: "12px",
                  background: msg.role === "user" ? "var(--color-accent-primary)" : "var(--color-bg-secondary)",
                  color: msg.role === "user" ? "white" : "var(--color-text-primary)",
                  fontSize: "13px", lineHeight: 1.6,
                }}>
                  {msg.content}
                </div>
              ))}
              {chatLoading && (
                <div style={{
                  alignSelf: "flex-start", padding: "10px 14px", borderRadius: "12px",
                  background: "var(--color-bg-secondary)", fontSize: "13px", color: "var(--color-text-muted)",
                }}>
                  Thinking...
                </div>
              )}
            </div>

            <div style={{
              padding: "12px", borderTop: "1px solid var(--color-border)",
              display: "flex", gap: "8px",
            }}>
              <input
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && sendMessage()}
                placeholder="Ask the coach..."
                style={{
                  flex: 1, padding: "10px 14px", borderRadius: "10px", border: "1px solid var(--color-border)",
                  background: "var(--color-bg-secondary)", color: "var(--color-text-primary)",
                  fontSize: "13px", outline: "none",
                }}
              />
              <button onClick={sendMessage} disabled={chatLoading} style={{
                padding: "10px 16px", borderRadius: "10px", border: "none",
                background: "var(--gradient-primary)", color: "white", fontWeight: 600,
                cursor: "pointer", fontSize: "14px",
              }}>↑</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Sample Data ───
const sampleCourses: Course[] = [
  { id: "1", title: "Understanding Stop Losses", description: "Learn how to protect your capital with proper stop loss placement. Covers fixed, trailing, and volatility-based stops with live practice scenarios.", difficulty: "beginner" },
  { id: "2", title: "Risk-Reward Mastery", description: "Master the art of favorable risk-reward setups. Learn to identify high-probability entries with optimal reward-to-risk ratios.", difficulty: "intermediate" },
  { id: "3", title: "Advanced Position Sizing", description: "Kelly criterion, fixed fractional, and volatility-adjusted position sizing strategies for consistent portfolio growth.", difficulty: "advanced" },
];

const sampleTrades = [
  { symbol: "AAPL", side: "long", entry_price: 150, exit_price: 148, quantity: 100, entry_time: "2024-01-01T10:00:00Z", exit_time: "2024-01-01T14:00:00Z", pnl: -200, duration_hours: 4 },
  { symbol: "AAPL", side: "long", entry_price: 147, exit_price: 144, quantity: 200, entry_time: "2024-01-01T14:30:00Z", exit_time: "2024-01-01T16:00:00Z", pnl: -600, duration_hours: 1.5 },
  { symbol: "AAPL", side: "long", entry_price: 143, exit_price: 140, quantity: 400, entry_time: "2024-01-01T16:30:00Z", exit_time: "2024-01-02T10:00:00Z", pnl: -1200, duration_hours: 17.5 },
  { symbol: "AAPL", side: "long", entry_price: 141, exit_price: 145, quantity: 50, entry_time: "2024-01-03T10:00:00Z", exit_time: "2024-01-03T15:00:00Z", pnl: 200, duration_hours: 5 },
];
