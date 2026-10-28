const cache = new Map<string, { value: unknown; updatedAt: number }>();
const pending = new Map<string, Promise<{ value: unknown; updatedAt: number }>>();
let generation = 0;

export function clearDashboardCache(notify = true) {
  generation++;
  cache.clear();
  pending.clear();
  if (notify && typeof window !== "undefined") window.dispatchEvent(new Event("dashboard-invalidated"));
}

export async function dashboardData<T>(key: string, fetcher: () => Promise<T>, force = false): Promise<{ value: T; updatedAt: number }> {
  const saved = cache.get(key);
  if (!force && saved && Date.now() - saved.updatedAt < 30_000) return saved as { value: T; updatedAt: number };
  const existing = pending.get(key);
  if (existing) return existing as Promise<{ value: T; updatedAt: number }>;
  const version = generation;
  const task = fetcher().then(value => {
    if (version !== generation) throw new Error("Account data changed. Please refresh.");
    const result = { value, updatedAt: Date.now() };
    cache.set(key, result);
    return result;
  }).finally(() => { if (version === generation) pending.delete(key); });
  pending.set(key, task);
  return task;
}
