import { Check, Loader2, ListMusic, Plus, Search } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import type { DragEvent } from 'react';
import { NavLink, useNavigate, useParams } from 'react-router-dom';

import { errorMessage } from '../api/client';
import { createPlaylist, getPlaylists, transferTracks } from '../api/spotify';
import { useToast } from '../context/ToastContext';
import type { PlaylistSummary } from '../types';

let sidebarLoadCount = 0;
let sidebarEffectCount = 0;

type DragPayload = {
  sourcePlaylistId: string;
  trackUris: string[];
};

type PendingDrop = {
  destination: PlaylistSummary;
  payload: DragPayload;
};

function parseDragPayload(data: DataTransfer): DragPayload | null {
  const raw = data.getData('application/json') || data.getData('text/plain');
  if (!raw) {
    return null;
  }

  try {
    const payload = JSON.parse(raw) as Partial<DragPayload>;
    if (
      typeof payload.sourcePlaylistId === 'string' &&
      Array.isArray(payload.trackUris) &&
      payload.trackUris.every((uri) => typeof uri === 'string')
    ) {
      return {
        sourcePlaylistId: payload.sourcePlaylistId,
        trackUris: payload.trackUris,
      };
    }
  } catch {
    return null;
  }

  return null;
}

export function PlaylistSidebar() {
  const navigate = useNavigate();
  const { playlistId } = useParams();
  const { notify } = useToast();
  const [playlists, setPlaylists] = useState<PlaylistSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [dragOverId, setDragOverId] = useState<string | null>(null);
  const [pendingDrop, setPendingDrop] = useState<PendingDrop | null>(null);
  const [busy, setBusy] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [newName, setNewName] = useState('');

  async function loadPlaylists() {
    sidebarLoadCount += 1;
    console.log(`[PlaylistSidebar] loadPlaylists #${sidebarLoadCount} invoked`);
    setLoading(true);
    try {
      setPlaylists(await getPlaylists({ source: 'PlaylistSidebar.loadPlaylists' }));
    } catch (err) {
      notify('error', errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    sidebarEffectCount += 1;
    console.log(`[PlaylistSidebar] useEffect #${sidebarEffectCount} -> loadPlaylists`);
    void loadPlaylists();
  }, []);

  const filteredPlaylists = useMemo(() => {
    const value = query.trim().toLowerCase();
    if (!value) {
      return playlists;
    }
    return playlists.filter((playlist) => playlist.name.toLowerCase().includes(value));
  }, [playlists, query]);

  async function handleCreatePlaylist() {
    const name = newName.trim();
    if (!name) {
      notify('error', 'Playlist name is required.');
      return;
    }

    setBusy(true);
    try {
      const playlist = await createPlaylist({ name, description: '', public: false });
      setPlaylists((current) => [playlist, ...current]);
      setNewName('');
      setCreateOpen(false);
      navigate(`/playlists/${playlist.id}`);
      notify('success', `Created ${playlist.name}.`);
    } catch (err) {
      notify('error', errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  function handleDragOver(event: DragEvent, playlist: PlaylistSummary) {
    if (!playlist.tracks_readable) {
      return;
    }
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    setDragOverId(playlist.id);
  }

  function handleDrop(event: DragEvent, destination: PlaylistSummary) {
    event.preventDefault();
    setDragOverId(null);

    const payload = parseDragPayload(event.dataTransfer);
    if (!payload || payload.trackUris.length === 0) {
      return;
    }

    if (payload.sourcePlaylistId === destination.id) {
      notify('info', 'Choose a different destination playlist.');
      return;
    }

    setPendingDrop({ destination, payload });
  }

  async function confirmDrop(action: 'copy' | 'move') {
    if (!pendingDrop) {
      return;
    }

    setBusy(true);
    try {
      const result = await transferTracks(action, {
        source_playlist_id: pendingDrop.payload.sourcePlaylistId,
        destination_playlist_id: pendingDrop.destination.id,
        track_uris: pendingDrop.payload.trackUris,
        skip_duplicates: true,
      });
      notify('success', `${action === 'copy' ? 'Copied' : 'Moved'} ${result.transferred} tracks.`);
      window.dispatchEvent(new CustomEvent('playlist-transfer-completed'));
      setPendingDrop(null);
    } catch (err) {
      notify('error', errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <aside className="hidden border-r border-line bg-[#0E141B] lg:block">
        <div className="flex h-full max-h-[calc(100vh-4rem)] flex-col p-4">
          <NavLink
            className={({ isActive }) =>
              `mb-4 block rounded-md px-3 py-2 text-sm ${isActive ? 'bg-spotify text-black' : 'text-slate-300 hover:bg-white/5'}`
            }
            to="/dashboard"
          >
            Dashboard
          </NavLink>

          <div className="flex items-center justify-between gap-2 border-b border-line pb-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Playlists</p>
            <span className="text-xs text-slate-500">{playlists.length.toLocaleString()}</span>
          </div>

          <label className="relative mt-3 block">
            <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
            <input
              className="h-9 w-full rounded-md border border-line bg-ink pl-9 pr-3 text-sm text-white"
              placeholder="Search playlist..."
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>

          <div className="mt-3 min-h-0 flex-1 overflow-y-auto pr-1 scrollbar-thin">
            {loading ? (
              <div className="space-y-2">
                {Array.from({ length: 8 }).map((_, index) => (
                  <div key={index} className="h-14 animate-pulse rounded-md bg-panel" />
                ))}
              </div>
            ) : (
              <div className="space-y-1">
                {filteredPlaylists.map((playlist) => {
                  const active = playlist.id === playlistId;
                  const disabled = !playlist.tracks_readable;
                  const image = playlist.images?.[0]?.url;

                  return (
                    <button
                      key={playlist.id}
                      className={`group flex w-full items-center gap-3 rounded-md border px-2 py-2 text-left transition ${
                        active
                          ? 'border-spotify bg-spotify/10'
                          : dragOverId === playlist.id
                            ? 'border-spotify bg-white/10'
                            : 'border-transparent hover:border-line hover:bg-white/5'
                      } ${disabled ? 'cursor-not-allowed opacity-55' : ''}`}
                      type="button"
                      disabled={disabled}
                      onClick={() => navigate(`/playlists/${playlist.id}`)}
                      onDragEnter={(event) => handleDragOver(event, playlist)}
                      onDragOver={(event) => handleDragOver(event, playlist)}
                      onDragLeave={() => setDragOverId((current) => (current === playlist.id ? null : current))}
                      onDrop={(event) => handleDrop(event, playlist)}
                      title={disabled ? 'Tracks are available only for playlists you own or collaborate on.' : playlist.name}
                    >
                      {image ? (
                        <img className="h-10 w-10 shrink-0 rounded object-cover" src={image} alt="" loading="lazy" />
                      ) : (
                        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded bg-[#1B2632]">
                          <ListMusic className="h-5 w-5 text-slate-500" />
                        </span>
                      )}
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium text-white">{playlist.name}</span>
                        <span className="block truncate text-xs text-slate-500">{playlist.tracks_total.toLocaleString()} tracks</span>
                      </span>
                      {active ? <Check className="h-4 w-4 shrink-0 text-spotify" /> : null}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div className="mt-3 border-t border-line pt-3">
            {createOpen ? (
              <div className="space-y-2">
                <input
                  className="h-9 w-full rounded-md border border-line bg-ink px-3 text-sm text-white"
                  placeholder="Playlist name"
                  value={newName}
                  onChange={(event) => setNewName(event.target.value)}
                />
                <div className="grid grid-cols-2 gap-2">
                  <button
                    className="h-9 rounded-md border border-line text-sm text-slate-200 hover:bg-white/5"
                    type="button"
                    onClick={() => setCreateOpen(false)}
                  >
                    Cancel
                  </button>
                  <button
                    className="inline-flex h-9 items-center justify-center gap-2 rounded-md bg-spotify text-sm font-semibold text-black hover:bg-[#22D363] disabled:opacity-60"
                    type="button"
                    disabled={busy}
                    onClick={() => void handleCreatePlaylist()}
                  >
                    {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                    Create
                  </button>
                </div>
              </div>
            ) : (
              <button
                className="inline-flex h-10 w-full items-center justify-center gap-2 rounded-md border border-line text-sm text-slate-200 hover:bg-white/5"
                type="button"
                onClick={() => setCreateOpen(true)}
              >
                <Plus className="h-4 w-4" />
                Create Playlist
              </button>
            )}
          </div>
        </div>
      </aside>

      {pendingDrop ? (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 p-4">
          <section className="w-full max-w-md rounded-md border border-line bg-panel shadow-soft">
            <header className="border-b border-line px-5 py-4">
              <h2 className="text-lg font-semibold text-white">
                Move {pendingDrop.payload.trackUris.length.toLocaleString()} tracks to {pendingDrop.destination.name}?
              </h2>
              <p className="mt-1 text-sm text-slate-400">Copy keeps the source playlist unchanged. Move removes them from the source after adding.</p>
            </header>
            <footer className="flex flex-col gap-3 px-5 py-4 sm:flex-row sm:justify-end">
              <button
                className="h-10 rounded-md border border-line px-4 text-sm text-slate-200 hover:bg-white/5"
                type="button"
                disabled={busy}
                onClick={() => setPendingDrop(null)}
              >
                Cancel
              </button>
              <button
                className="h-10 rounded-md border border-line px-4 text-sm font-semibold text-white hover:bg-white/5 disabled:opacity-60"
                type="button"
                disabled={busy}
                onClick={() => void confirmDrop('copy')}
              >
                Copy
              </button>
              <button
                className="inline-flex h-10 items-center justify-center gap-2 rounded-md bg-spotify px-4 text-sm font-semibold text-black hover:bg-[#22D363] disabled:opacity-60"
                type="button"
                disabled={busy}
                onClick={() => void confirmDrop('move')}
              >
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Move
              </button>
            </footer>
          </section>
        </div>
      ) : null}
    </>
  );
}
