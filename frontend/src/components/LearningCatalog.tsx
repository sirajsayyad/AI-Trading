"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { categories, Course, SavedLesson, duration, learning, lessonUrl } from "@/lib/learning";
import "@/app/training/learning.css";
import { useAuth } from "@/contexts/AuthContext";

function CourseCard({ course: c }: { course: Course }) {
  return <article className="card learn-course">
    <Link href={`/training/${c.id}`} aria-label={`View ${c.title}`}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      {c.thumbnail ? <img loading="lazy" src={c.thumbnail} alt="" className="learn-thumbnail" /> : <div className="learn-thumbnail learn-art" aria-hidden="true"><span>{c.category}</span><svg viewBox="0 0 200 55"><path d="M0 45L22 35L42 42L65 18L86 26L110 8L131 22L150 15L175 4L200 10" fill="none" stroke="currentColor" strokeWidth="2" /></svg></div>}
      <div className="learn-meta"><span className={`learn-badge ${c.difficulty}`}>{c.difficulty}</span><span>{c.lecture_count} lessons</span></div>
      <h3>{c.title}</h3>
    </Link>
    <p className="learn-provider">{c.provider} · {c.instructor}</p>
    <p className="learn-meta">{c.category}</p><p>{c.description}</p>
    <p className="learn-meta">~{duration(c.duration_seconds)} · {c.language}<br />{c.subtitles}</p>
    <div className="learn-progress"><progress max={100} value={c.progress} aria-label={`${c.title} completion`} /><span>{c.progress}%</span></div>
    <div className="learn-meta"><span>{c.progress === 100 ? "Completed" : c.enrolled ? "Enrolled" : "Open for enrollment"}</span><span>{c.enrollment_count} enrolled</span></div>
    <Link className="learn-button" href={c.enrolled && c.last_lesson_id ? lessonUrl(c.id, c.last_lesson_id) : `/training/${c.id}`}>{c.enrolled ? "Continue Learning" : "Start Learning"} <span aria-hidden="true">→</span></Link>
  </article>;
}

export default function LearningCatalog() {
  const { user, loading: authLoading } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [saved, setSaved] = useState<SavedLesson[]>([]);
  const [completed, setCompleted] = useState<{ lesson_id: string; title: string; course_id: string }[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [difficulty, setDifficulty] = useState("");
  const [sort, setSort] = useState("recent");
  const [tab, setTab] = useState("explore");
  function load() {
    return Promise.all([learning.courses(), learning.saved(), learning.completed()]).then(([c, b, done]) => { setCourses(c); setSaved(b); setCompleted(done); setError(""); }).catch(e => setError(e.message)).finally(() => setLoading(false));
  }
  useEffect(() => { if (user) void load(); }, [user]);
  const enrolled = courses.filter(c => c.enrolled);
  const visible = courses.filter(c => (tab !== "mine" || c.enrolled) && (tab !== "replay" || c.practice_mode === "replay") && (tab !== "backtest" || c.practice_mode === "backtest") && (tab !== "risk" || c.category === categories[2]) && (!category || c.category === category) && (!difficulty || c.difficulty === difficulty) && `${c.title} ${c.description} ${c.provider}`.toLowerCase().includes(query.toLowerCase())).sort((a, b) => sort === "popular" ? b.enrollment_count - a.enrollment_count : sort === "duration" ? a.duration_seconds - b.duration_seconds : Date.parse(b.created_at) - Date.parse(a.created_at));
  if (authLoading) return <p role="status">Loading your session…</p>;
  if (!user) return <section className="learning card"><h2>Your learning workspace</h2><p>Sign in to explore courses and save progress to your account.</p><Link className="learn-button" href="/login">Sign in to learn</Link></section>;
  return <section className="learning" aria-label="Course learning">
    {error && <div className="learn-error" role="alert">{error} <button onClick={load}>Retry</button></div>}
    {loading ? <p role="status">Loading your learning workspace…</p> : <>
      <h2>Continue Learning</h2>
      {enrolled.length ? <div className="learn-resume-grid">{enrolled.map(c => <Link className="card learn-resume" href={c.last_lesson_id ? lessonUrl(c.id, c.last_lesson_id) : `/training/${c.id}`} key={c.id}><span className="learn-eyebrow">{c.progress === 100 ? "COURSE COMPLETED" : "PICK UP WHERE YOU LEFT OFF"}</span><h3>{c.title}</h3><p>{c.last_lesson_title || "Begin your first lesson"}</p><div className="learn-progress"><progress max={100} value={c.progress} aria-label="Course progress" /><span>{c.progress}%</span></div><span className="learn-link">Continue Learning →</span></Link>)}</div> : <div className="card learn-empty">Your next skill starts here. Enroll in a course below to save your place.</div>}
      <nav className="learn-tabs" aria-label="Learning sections"><button aria-pressed={tab === "explore"} onClick={() => setTab("explore")}>AI Trading Courses</button><button aria-pressed={tab === "mine"} onClick={() => setTab("mine")}>My Learning Progress ({enrolled.length})</button>{[["replay", "Replay Training"], ["backtest", "Backtesting Academy"], ["risk", "Risk Management"]].map(([id, name]) => <button key={id} aria-pressed={tab === id} onClick={() => setTab(id)}>{name}</button>)}</nav>
      {tab === "mine" && <div className="card learn-summary"><h3>My Learning Progress</h3><p>{enrolled.reduce((n, c) => n + c.completed_lectures, 0)} completed lessons · {enrolled.filter(c => c.progress === 100).length} completed courses · {saved.length} saved notes</p><h4>Saved lessons</h4>{saved.length ? saved.map(b => <Link key={`${b.lesson_id}-${b.position}`} href={lessonUrl(b.course_id, b.lesson_id, b.position)} className="learn-saved">{b.title} · {Math.floor(b.position / 60)}:{String(b.position % 60).padStart(2, "0")} — {b.notes || "Bookmark"}</Link>) : <p>No saved lessons yet.</p>}</div>}
      <h2>Learning Categories</h2>
      {tab === "mine" && <details className="card"><summary>Completed lessons ({completed.length})</summary>{completed.length ? completed.map(l => <Link key={l.lesson_id} className="learn-saved" href={lessonUrl(l.course_id, l.lesson_id)}>✓ {l.title}</Link>) : <p>No completed lessons yet.</p>}</details>}
      <div className="learn-categories"><button aria-pressed={!category} onClick={() => setCategory("")}>All topics</button>{categories.map(c => <button key={c} aria-pressed={category === c} onClick={() => setCategory(c)}>{c}</button>)}</div>
      <div className="learn-filters"><label>Search courses<input value={query} onChange={e => setQuery(e.target.value)} placeholder="Title, topic or provider" type="search" /></label><label>Difficulty<select value={difficulty} onChange={e => setDifficulty(e.target.value)}><option value="">All levels</option>{["beginner", "intermediate", "advanced"].map(d => <option key={d}>{d}</option>)}</select></label><label>Sort by<select value={sort} onChange={e => setSort(e.target.value)}><option value="recent">Recently added</option><option value="popular">Popularity</option><option value="duration">Shortest duration</option></select></label></div>
      <p className="learn-meta" aria-live="polite">{visible.length} courses · Durations are estimates</p>
      <div className="learn-grid">{visible.map(c => <CourseCard key={c.id} course={c} />)}</div>
      {!visible.length && <div className="card learn-empty">No courses match these filters.</div>}
    </>}
  </section>;
}
