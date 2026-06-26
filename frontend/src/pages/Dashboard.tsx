import { RefreshCw } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { errorMessage } from '../api/client';
import { getPlaylists } from '../api/spotify';
import { PlaylistCard } from '../components/PlaylistCard';
import { useToast } from '../context/ToastContext';
import type { PlaylistSummary } from '../types';

export function Dashboard() {
  const navigate = useNavigate();
  const { notify } = useToast();
  const [playlists, setPlaylists] = useState<PlaylistSummary[]>([]);
  const [loading, setLoading] = useState(true);

  async function loadPlaylists() {
    setLoading(true);
    try {
      setPlaylists(await getPlaylists());
    } catch (err) {
      notify('error', errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadPlaylists();
  }, []);

  return (
    <section>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-spotify">Dashboard</p>
          <h1 className="mt-1 text-3xl font-semibold text-white">Choose a source playlist</h1>
        </div>
        <button
          className="inline-flex h-10 items-center justify-center gap-2 rounded-md border border-line px-3 text-sm text-slate-200 hover:bg-white/5"
          type="button"
          onClick={() => void loadPlaylists()}
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="mt-8 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
          {Array.from({ length: 10 }).map((_, index) => (
            <div key={index} className="h-72 animate-pulse rounded-md border border-line bg-panel" />
          ))}
        </div>
      ) : (
        <div className="mt-8 grid grid-cols-2 gap-4 md:grid-cols-3 xl:grid-cols-5">
          {playlists.map((playlist) => (
            <PlaylistCard
              key={playlist.id}
              playlist={playlist}
              onSelect={() => navigate(`/playlists/${playlist.id}`)}
            />
          ))}
        </div>
      )}
    </section>
  );
}
