"use client";
import { use, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import dynamic from "next/dynamic";
import CoachChat from "@/components/CoachChat";
import TradingExercise from "@/components/TradingExercise";
import ReactMarkdown from "react-markdown";
import { Course, Lesson, learning, lessonUrl } from "@/lib/learning";
import "../../../learning.css";

const LessonVideo = dynamic(() => import("@/components/LessonVideo"), { ssr: false });

export default function PlayerPage({ params }: { params: Promise<{ courseId: string; lessonId: string }> }) {
  const { courseId, lessonId } = use(params);
  return <LessonWorkspace key={`${courseId}/${lessonId}`} courseId={courseId} lessonId={lessonId} />;
}

function LessonWorkspace({ courseId, lessonId }: { courseId: string; lessonId: string }) {
  const search = useSearchParams();
  const [course, setCourse] = useState<Course | null>(null);
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [notes, setNotes] = useState("");
  const [seek, setSeek] = useState<number | null>(null);
  const [answers, setAnswers] = useState<number[]>([]);
  const [quizResult, setQuizResult] = useState("");
  const [busy, setBusy] = useState(false);
  const position = useRef(0);
  const queue = useRef(Promise.resolve());
  const active = useRef(true);
  useEffect(() => {
    active.current = true;
    learning.course(courseId).then(async c => {
      if (!c.modules.some(m => m.lessons.some(l => l.id === lessonId))) throw new Error("This lesson does not belong to this course");
      const l = await learning.lesson(lessonId);
      if (!active.current) return;
      position.current = l.position;
      setCourse(c); setLesson(l);
      learning.progress(lessonId, l.position).catch(e => { if (active.current) setError(e.message); });
    }).catch(e => { if (active.current) setError(e.message); });
    return () => { active.current = false; };
  }, [courseId, lessonId]);
  const lessons = course?.modules.flatMap(m => m.lessons) || [];
  const index = lessons.findIndex(l => l.id === lessonId);
  function progress(time: number, complete: boolean) {
    position.current = time;
    // Serialize writes so a delayed pause cannot overwrite a newer saved position.
    queue.current = queue.current.then(async () => {
      await learning.progress(lessonId, time, complete);
      if (active.current) {
        setStatus("Progress saved");
        if (complete) { setLesson(l => l ? { ...l, completed: true } : l); setCourse(await learning.course(courseId)); }
      }
    }).catch(e => { if (active.current) setError(`Could not save progress: ${e.message}`); });
    return queue.current;
  }
  async function bookmark() {
    setBusy(true); setError("");
    try {
      const at = Math.round(position.current);
      await learning.bookmark(lessonId, at, notes);
      setLesson(l => l ? { ...l, bookmarks: [...l.bookmarks.filter(b => b.position !== at), { position: at, notes }].sort((a, b) => a.position - b.position) } : l);
      setStatus("Note and bookmark saved"); setNotes("");
    } catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  async function removeBookmark(at: number) {
    try { await learning.deleteBookmark(lessonId, at); setLesson(l => l ? { ...l, bookmarks: l.bookmarks.filter(b => b.position !== at) } : l); }
    catch (e) { setError((e as Error).message); }
  }
  async function quiz() {
    setBusy(true); setError("");
    try { const r = await learning.quiz(lessonId, answers); setQuizResult(`${r.score}% — ${r.passed ? "Passed" : "Review the lesson and try again"}. ${r.feedback.map(f => `Correct answer: ${f.answer}`).join(" ")}`); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  const requested = Number(search.get("t"));
  const initialPosition = search.has("t") && Number.isFinite(requested) && requested >= 0 && requested <= 86400 ? requested : lesson?.position || 0;
  return <div className="learning">
    <Link className="learn-link" href={`/training/${courseId}`}>← Course overview</Link>
    {error && <div className="learn-error" role="alert">{error} <button onClick={() => window.location.reload()}>Reload lesson</button></div>}
    {!lesson || !course ? !error && <p role="status">Loading lesson…</p> : <>
      <p className="learn-eyebrow">{course.title} · LESSON {index + 1} OF {lessons.length}</p><h1>{lesson.title}</h1>
      <div className="learn-player-layout"><div>
        {lesson.video_id ? <LessonVideo videoId={lesson.video_id} initialPosition={initialPosition} seekPosition={seek} onProgress={progress} onPosition={time => { position.current = time; }} /> : <p className="learn-meta">Reading lesson · Read the notes and complete the knowledge check below.</p>}
        <div className="learn-actions"><span>{index > 0 && <Link className="learn-button" href={lessonUrl(courseId, lessons[index - 1].id)}>← Previous Lecture</Link>}</span><button className="learn-button" disabled={lesson.completed || busy} onClick={async () => { setBusy(true); await progress(position.current, true); setBusy(false); }}>{lesson.completed ? "✓ Completed" : "Mark as Complete"}</button>{index < lessons.length - 1 && <Link className="learn-button" href={lessonUrl(courseId, lessons[index + 1].id)}>Next Lecture →</Link>}</div>
        <p className="learn-status" role="status">{status}</p>
        <section className="card learn-reading"><h2>Lesson notes</h2><ReactMarkdown>{lesson.content_markdown}</ReactMarkdown>{course.license.includes("CC BY 4.0") && <a className="learn-button" download={`${lesson.id}-notes.md`} href={`data:text/markdown;charset=utf-8,${encodeURIComponent(`# ${lesson.title}\n\n${lesson.content_markdown}\n\nAITrade supplementary notes. CC BY 4.0: https://creativecommons.org/licenses/by/4.0/`)}`}>Download AITrade notes</a>}<h3>Key takeaways</h3><ul>{lesson.takeaways?.map(t => <li key={t}>{t}</li>)}</ul>{lesson.replay_scenario && <p><Link className="learn-link" href={`/replay?symbol=${encodeURIComponent(lesson.replay_scenario.symbol)}`}>Practice {lesson.replay_scenario.symbol} in Replay →</Link></p>}</section>
        <TradingExercise course={course} lessonId={lessonId} />
        <section className="card" style={{ marginTop: 20 }}><h2>Notes & bookmarks</h2><label htmlFor="lesson-note">Your note at the current playback position</label><textarea id="lesson-note" maxLength={10000} rows={3} value={notes} onChange={e => setNotes(e.target.value)} /><button className="learn-button" disabled={busy} onClick={bookmark}>Save note / bookmark</button>{lesson.bookmarks.map(b => <div className="learn-saved" key={b.position}><button className="learn-link" onClick={() => { setSeek(b.position); position.current = b.position; setNotes(b.notes); }}>{Math.floor(b.position / 60)}:{String(b.position % 60).padStart(2, "0")} — {b.notes || "Bookmark"}</button><button className="learn-button" style={{ marginLeft: 12 }} onClick={() => removeBookmark(b.position)}>Remove</button></div>)}</section>
        {!!lesson.quiz?.length && <section className="card learn-quiz" style={{ marginTop: 20 }}><h2>Knowledge check</h2>{lesson.quiz.map((q, qi) => <fieldset key={qi}><legend>{q.question}</legend>{q.options.map((o, oi) => <label key={o}><input type="radio" name={`question-${qi}`} checked={answers[qi] === oi} onChange={() => setAnswers(prev => { const next = [...prev]; next[qi] = oi; return next; })} />{o}</label>)}</fieldset>)}<button className="learn-button" disabled={busy || lesson.quiz.some((_, i) => answers[i] === undefined)} onClick={quiz}>Submit answers</button><p role="status">{quizResult}</p>{lesson.quiz_attempts.length > 0 && <p className="learn-meta">Last saved attempt: {lesson.quiz_attempts[0].score}% · {lesson.quiz_attempts.length} recent attempts</p>}</section>}
        <CoachChat key={lessonId} courseId={courseId} lessonId={lessonId} lessonTitle={lesson.title} />
      </div><aside><details className="card learn-curriculum" open><summary>Course curriculum · {course.progress}%</summary>{course.modules.map(m => <section key={m.id}><h3>{m.title}</h3>{m.lessons.map(l => <Link key={l.id} aria-current={l.id === lessonId ? "page" : undefined} href={lessonUrl(courseId, l.id)}>{l.completed ? "✓ " : ""}{l.title}</Link>)}</section>)}</details><section className="card" style={{ marginTop: 18 }}><h3>Related lessons</h3>{lessons.filter(l => l.id !== lessonId).slice(0, 3).map(l => <Link className="learn-saved" key={l.id} href={lessonUrl(courseId, l.id)}>{l.title}</Link>)}<p className="learn-meta">{course.provider}<br />{course.license}</p></section></aside></div>
    </>}
  </div>;
}
