import { Music, ShieldCheck } from 'lucide-react';
import { Navigate } from 'react-router-dom';

import { LoadingScreen } from '../components/LoadingScreen';
import { useAuth } from '../context/AuthContext';

export function Login() {
  const { user, loading, loginUrl } = useAuth();
  if (loading) {
    return <LoadingScreen />;
  }
  if (user) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4 py-10 text-white">
      <section className="w-full max-w-xl rounded-md border border-line bg-panel p-6 shadow-soft sm:p-8">
        <div className="flex items-center gap-3">
          <span className="flex h-12 w-12 items-center justify-center rounded bg-spotify text-black">
            <Music className="h-6 w-6" />
          </span>
          <div>
            <h1 className="text-2xl font-semibold">Spotify Playlist Bulk Transfer Manager</h1>
            <p className="text-sm text-slate-400">Move or copy selected tracks between playlists.</p>
          </div>
        </div>
        <a
          className="mt-8 inline-flex h-12 w-full items-center justify-center gap-2 rounded-md bg-spotify px-5 font-semibold text-black hover:bg-[#22D363]"
          href={loginUrl}
        >
          <ShieldCheck className="h-5 w-5" />
          Login with Spotify
        </a>
        <p className="mt-4 text-sm text-slate-400">
          OAuth tokens are stored server-side and scoped to playlist management permissions.
        </p>
      </section>
    </main>
  );
}
