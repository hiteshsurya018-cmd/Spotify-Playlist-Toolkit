import { LogOut, Music2 } from 'lucide-react';
import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';
import { PlaylistSidebar } from './PlaylistSidebar';

export function AppLayout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const avatar = user?.images?.[0]?.url;

  return (
    <div className="min-h-screen bg-ink text-slate-100">
      <header className="sticky top-0 z-30 border-b border-line bg-ink/90 backdrop-blur">
        <div className="flex h-16 items-center justify-between px-4 sm:px-6">
          <Link className="flex min-w-0 items-center gap-3" to="/dashboard">
            <span className="flex h-9 w-9 items-center justify-center rounded bg-spotify text-black">
              <Music2 className="h-5 w-5" />
            </span>
            <span className="truncate text-base font-semibold">Playlist Transfer</span>
          </Link>
          <div className="flex min-w-0 items-center gap-3">
            <div className="hidden min-w-0 items-center gap-3 sm:flex">
              {avatar ? (
                <img className="h-8 w-8 rounded-full object-cover" src={avatar} alt="" />
              ) : (
                <div className="h-8 w-8 rounded-full bg-slate-700" />
              )}
              <span className="max-w-40 truncate text-sm text-slate-300">{user?.display_name ?? 'Spotify user'}</span>
            </div>
            <button
              className="inline-flex h-10 items-center gap-2 rounded-md border border-line px-3 text-sm text-slate-200 hover:border-slate-500 hover:bg-white/5"
              type="button"
              onClick={() => void logout()}
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </div>
      </header>
      <div className="grid min-h-[calc(100vh-4rem)] grid-cols-1 lg:grid-cols-[16rem_1fr]">
        <PlaylistSidebar />
        <main className="min-w-0 p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}
