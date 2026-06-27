import { ArrowDownUp, CheckSquare, Square } from 'lucide-react';
import type { DragEvent } from 'react';

import type { Track } from '../types';
import { formatDuration } from '../utils/format';

type Props = {
  tracks: Track[];
  sourcePlaylistId: string;
  selectedUris: Set<string>;
  sortBy: string;
  sortOrder: 'asc' | 'desc';
  onToggle: (uri: string) => void;
  onToggleAllVisible: () => void;
  onSort: (column: string) => void;
};

export function TrackTable({ tracks, sourcePlaylistId, selectedUris, sortBy, sortOrder, onToggle, onToggleAllVisible, onSort }: Props) {
  const allVisibleSelected = tracks.length > 0 && tracks.every((track) => selectedUris.has(track.uri));

  function handleDragStart(event: DragEvent<HTMLTableRowElement>, track: Track) {
    const trackUris = selectedUris.has(track.uri) ? [...selectedUris] : [track.uri];
    const payload = JSON.stringify({
      sourcePlaylistId,
      trackUris,
    });

    event.dataTransfer.effectAllowed = 'copyMove';
    event.dataTransfer.setData('application/json', payload);
    event.dataTransfer.setData('text/plain', payload);
  }

  return (
    <div className="overflow-hidden rounded-md border border-line">
      <div className="max-h-[62vh] overflow-auto scrollbar-thin">
        <table className="min-w-[900px] w-full border-collapse text-left text-sm">
          <thead className="sticky top-0 z-10 bg-[#121A23] text-xs uppercase tracking-wide text-slate-400">
            <tr>
              <th className="w-12 px-4 py-3">
                <button
                  className="rounded p-1 hover:bg-white/10"
                  type="button"
                  onClick={onToggleAllVisible}
                  aria-label={allVisibleSelected ? 'Deselect visible tracks' : 'Select visible tracks'}
                >
                  {allVisibleSelected ? <CheckSquare className="h-5 w-5 text-spotify" /> : <Square className="h-5 w-5" />}
                </button>
              </th>
              <th className="w-16 px-2 py-3">Art</th>
              {[
                ['name', 'Song Name'],
                ['artist', 'Artist'],
                ['album', 'Album'],
                ['duration_ms', 'Duration'],
              ].map(([column, label]) => (
                <th key={column} className="px-4 py-3">
                  <button
                    className="inline-flex items-center gap-2 rounded px-1 py-0.5 hover:bg-white/10"
                    type="button"
                    onClick={() => onSort(column)}
                  >
                    {label}
                    <ArrowDownUp className={`h-3.5 w-3.5 ${sortBy === column ? 'text-spotify' : 'text-slate-500'}`} />
                    {sortBy === column ? <span className="sr-only">{sortOrder}</span> : null}
                  </button>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-line bg-panel">
            {tracks.map((track) => (
              <tr
                key={track.uri}
                className="cursor-grab hover:bg-white/[0.03] active:cursor-grabbing"
                draggable
                onDragStart={(event) => handleDragStart(event, track)}
              >
                <td className="px-4 py-3">
                  <input
                    checked={selectedUris.has(track.uri)}
                    className="h-4 w-4 accent-spotify"
                    type="checkbox"
                    onChange={() => onToggle(track.uri)}
                    aria-label={`Select ${track.name}`}
                  />
                </td>
                <td className="px-2 py-3">
                  {track.album_art ? (
                    <img className="h-11 w-11 rounded object-cover" src={track.album_art} alt="" loading="lazy" />
                  ) : (
                    <div className="h-11 w-11 rounded bg-slate-800" />
                  )}
                </td>
                <td className="max-w-xs px-4 py-3">
                  <p className="truncate font-medium text-white">{track.name}</p>
                </td>
                <td className="max-w-xs px-4 py-3 text-slate-300">
                  <span className="line-clamp-2">{track.artists.join(', ')}</span>
                </td>
                <td className="max-w-xs px-4 py-3 text-slate-300">
                  <span className="line-clamp-2">{track.album}</span>
                </td>
                <td className="px-4 py-3 text-slate-300">{formatDuration(track.duration_ms)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {tracks.length === 0 ? <p className="bg-panel px-4 py-10 text-center text-sm text-slate-400">No tracks match the filters.</p> : null}
      </div>
    </div>
  );
}
