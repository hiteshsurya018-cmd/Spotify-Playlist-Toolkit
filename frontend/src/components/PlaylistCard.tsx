import { ListMusic, Lock } from 'lucide-react';

import type { PlaylistSummary } from '../types';

export function PlaylistCard({ playlist, onSelect }: { playlist: PlaylistSummary; onSelect: () => void }) {
  const image = playlist.images?.[0]?.url;
  const disabled = !playlist.tracks_readable;

  return (
    <button
      className="group flex min-h-40 w-full flex-col rounded-md border border-line bg-panel p-4 text-left transition hover:-translate-y-0.5 hover:border-spotify hover:bg-[#16202A] disabled:cursor-not-allowed disabled:opacity-60 disabled:hover:translate-y-0 disabled:hover:border-line disabled:hover:bg-panel"
      type="button"
      disabled={disabled}
      onClick={onSelect}
      title={disabled ? 'Tracks are available only for playlists you own or collaborate on.' : playlist.name}
    >
      {image ? (
        <img className="aspect-square w-full rounded object-cover" src={image} alt="" loading="lazy" />
      ) : (
        <div className="flex aspect-square w-full items-center justify-center rounded bg-[#1B2632]">
          <ListMusic className="h-10 w-10 text-slate-500" />
        </div>
      )}
      <div className="mt-4 min-w-0">
        <h2 className="truncate text-base font-semibold text-white">{playlist.name}</h2>
        <p className="mt-1 truncate text-sm text-slate-400">{playlist.owner}</p>
        <div className="mt-3 flex items-center justify-between gap-2 text-sm text-slate-300">
          <span>{playlist.tracks_total.toLocaleString()} tracks</span>
          {disabled ? <Lock className="h-4 w-4 shrink-0 text-slate-500" aria-label="Tracks unavailable" /> : null}
        </div>
      </div>
    </button>
  );
}
