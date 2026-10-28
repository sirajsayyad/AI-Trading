export default function Loading() {
  return (
    <div className="route-loading" role="status" aria-label="Loading page">
      <div className="route-loading-spinner" />
      <span>Loading workspace…</span>
    </div>
  );
}
