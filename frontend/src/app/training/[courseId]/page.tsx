"use client";
import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Course, duration, learning, lessonUrl } from "@/lib/learning";
import "../learning.css";

export default function CoursePage({ params }: { params: Promise<{ courseId: string }> }) {
  const { courseId } = use(params);
  const router = useRouter();
  const [course, setCourse] = useState<Course | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { learning.course(courseId).then(setCourse).catch(e => setError(e.message)); }, [courseId]);
  async function start() {
    if (!course?.last_lesson_id) return;
    setBusy(true); setError("");
    try { await learning.enroll(courseId); router.push(lessonUrl(courseId, course.last_lesson_id)); }
    catch (e) { setError((e as Error).message); setBusy(false); }
  }
  return <div className="learning learn-detail"><Link className="learn-link" href="/training">← All courses</Link>
    {error && <p className="learn-error" role="alert">{error} <button onClick={() => { learning.course(courseId).then(c => { setCourse(c); setError(""); }).catch(e => setError(e.message)); }}>Retry</button></p>}
    {!course ? !error && <p role="status">Loading course…</p> : <>
      <div className="learn-detail-head"><section><p className="learn-eyebrow">{course.category} / {course.difficulty}</p><h1>{course.title}</h1><p>{course.description}</p><h2>What you’ll learn</h2><ul>{course.objectives?.map(o => <li key={o}>{o}</li>)}</ul><h3>Prerequisites</h3><p>{course.prerequisites}</p></section><aside className="card"><p className="learn-link">{course.instructor}</p><p>{course.provider}</p><p>~{duration(course.duration_seconds)} · {course.lecture_count} lessons</p><p>{course.language} · {course.subtitles}</p><p>{course.completed_lectures} completed · {course.progress}%</p><progress max={100} value={course.progress} aria-label="Course completion" /><button className="learn-button" disabled={busy || !course.last_lesson_id} onClick={start}>{busy ? "Opening…" : course.enrolled ? "Continue Learning" : "Enroll & Start Learning"}</button><p className="learn-meta">{course.license}</p>{course.license_url && <a className="learn-link" href={course.license_url} target="_blank" rel="noreferrer">License / terms ↗</a>}{course.source_url && <p><a className="learn-link" href={course.source_url} target="_blank" rel="noreferrer">Original provider page ↗</a></p>}</aside></div>
      <h2>Course curriculum</h2><div className="learn-curriculum">{course.modules.map(m => <details className="card" open key={m.id}><summary>{m.title}</summary>{m.lessons.map((l, i) => course.enrolled ? <Link key={l.id} href={lessonUrl(course.id, l.id)}>{l.completed ? "✓" : String(i + 1).padStart(2, "0")} · {l.title} <span className="learn-meta">{l.kind}</span></Link> : <p key={l.id}>{i + 1}. {l.title} · {l.kind}</p>)}</details>)}</div>
    </>}
  </div>;
}
