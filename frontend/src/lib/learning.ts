import { request } from "./api";

export const categories = ["AI Trading Fundamentals", "Technical Analysis for Trading", "Risk Management and Position Sizing", "Trading Strategy Development", "Trading Replay and Simulation", "AI Trading Strategy Backtesting", "Quantitative and Algorithmic Trading", "Trading Psychology and Behavioral Analytics", "Portfolio and Market Risk Analysis", "AI Model Evaluation for Trading"];
export type Course = {
  id: string; title: string; description: string; difficulty: string; category: string;
  provider: string; instructor: string; license: string; license_url?: string; source_url: string;
  practice_mode?: "replay" | "backtest"; resources?: { provider: string; url: string; title: string; usage: string }[];
  thumbnail?: string; language: string; subtitles: string; objectives: string[]; prerequisites: string;
  duration_seconds: number; lecture_count: number; enrolled: boolean; progress: number;
  enrollment_count: number; completed_lectures: number; last_lesson_id: string | null;
  last_lesson_title: string | null; created_at: string;
  modules: { id: string; title: string; lessons: { id: string; title: string; kind: string; completed: boolean }[] }[];
};
export type SavedLesson = { lesson_id: string; title: string; course_id: string; position: number; notes: string };
export type Lesson = {
  id: string; title: string; content_markdown: string; video_id?: string; kind: string;
  position: number; completed: boolean; takeaways: string[];
  bookmarks: { position: number; notes: string }[];
  quiz: { question: string; options: string[] }[]; quiz_attempts: { score: number; attempted_at: string }[];
  replay_scenario?: { symbol: string; timeframe: string; start_date: string; blind_mode: boolean };
};
export const learning = {
  courses: () => request<Course[]>("/courses"),
  course: (id: string) => request<Course>(`/courses/${encodeURIComponent(id)}`),
  enroll: (id: string) => request(`/courses/${encodeURIComponent(id)}/enroll`, { method: "POST" }),
  lesson: (id: string) => request<Lesson>(`/lessons/${encodeURIComponent(id)}`),
  progress: (id: string, position: number, completed = false) => request(`/lessons/${encodeURIComponent(id)}/progress`, { method: "PUT", body: { position, completed } }),
  bookmark: (id: string, position: number, notes: string) => request(`/lessons/${encodeURIComponent(id)}/bookmark`, { method: "PUT", body: { position, notes } }),
  deleteBookmark: (id: string, position: number) => request(`/lessons/${encodeURIComponent(id)}/bookmark/${position}`, { method: "DELETE" }),
  saved: () => request<SavedLesson[]>("/learning/saved"),
  completed: () => request<{ lesson_id: string; title: string; course_id: string }[]>("/learning/completed"),
  quiz: (id: string, answers: number[]) => request<{ score: number; passed: boolean; feedback: { correct: boolean; answer: string }[] }>(`/lessons/${encodeURIComponent(id)}/quiz`, { method: "POST", body: { answers } }),
  coach: (id: string, question: string) => request<{ answer: string }>(`/lessons/${encodeURIComponent(id)}/coach`, { method: "POST", body: { question } }),
};
export const duration = (seconds: number) => `${Math.max(1, Math.round(seconds / 60))} min`;
export const lessonUrl = (course: string, lesson: string, position?: number) => `/training/${encodeURIComponent(course)}/learn/${encodeURIComponent(lesson)}${position === undefined ? "" : `?t=${position}`}`;
