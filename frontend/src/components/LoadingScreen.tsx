import { Loader2 } from 'lucide-react';

export function LoadingScreen() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-ink text-white">
      <div className="flex items-center gap-3 rounded-md border border-line bg-panel px-5 py-4">
        <Loader2 className="h-5 w-5 animate-spin text-spotify" />
        <span className="text-sm text-slate-200">Loading</span>
      </div>
    </main>
  );
}
