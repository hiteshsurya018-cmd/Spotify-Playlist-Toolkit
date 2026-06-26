export function ProgressBar({ value }: { value: number }) {
  const percent = Math.max(0, Math.min(100, value));
  return (
    <div className="h-2 w-full overflow-hidden rounded bg-slate-800" aria-label={`Progress ${percent}%`}>
      <div className="h-full bg-spotify transition-all duration-300" style={{ width: `${percent}%` }} />
    </div>
  );
}
