"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

export default function TrainingExerciseBanner() {
  const params = useSearchParams();
  const course = params.get("course") || "";
  const lesson = params.get("lesson") || "";
  if (!/^[\w-]+$/.test(course) || !/^[\w-]+$/.test(lesson)) return null;
  return <div className="card" style={{ marginBottom: 20, borderColor: "#08767b" }}><strong>Training exercise · simulation only</strong><p style={{ margin: "10px 0", color: "var(--color-text-secondary)" }}>Record your entry, exit and risk rules before running the exercise. Review the calculated results against those rules, then save your observations in the lesson notes.</p><Link href={`/training/${course}/learn/${lesson}`} style={{ color: "#67e8f9" }}>← Return to lesson and decision review</Link></div>;
}
