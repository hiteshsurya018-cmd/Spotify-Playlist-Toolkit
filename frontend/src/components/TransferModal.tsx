import { Loader2, Plus, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';

import { errorMessage } from '../api/client';
import { createPlaylist, detectDuplicates, transferTracks } from '../api/spotify';
import { useToast } from '../context/ToastContext';
import type { DuplicateSummary, PlaylistSummary, TransferResult } from '../types';
import { ProgressBar } from './ProgressBar';

type Props = {
  open: boolean;
  sourcePlaylistId: string;
  playlists: PlaylistSummary[];
  selectedUris: string[];
  onClose: () => void;
  onCompleted: (result: TransferResult) => void;
  onPlaylistCreated: (playlist: PlaylistSummary) => void;
};

export function TransferModal({
  open,
  sourcePlaylistId,
  playlists,
  selectedUris,
  onClose,
  onCompleted,
  onPlaylistCreated,
}: Props) {
  const { notify } = useToast();
  const destinations = useMemo(
    () => playlists.filter((playlist) => playlist.id !== sourcePlaylistId && playlist.tracks_readable),
    [playlists, sourcePlaylistId],
  );
  const [destinationId, setDestinationId] = useState('');
  const [skipDuplicates, setSkipDuplicates] = useState(true);
  const [duplicates, setDuplicates] = useState<DuplicateSummary | null>(null);
  const [checking, setChecking] = useState(false);
  const [progress, setProgress] = useState(0);
  const [busy, setBusy] = useState(false);
  const [createMode, setCreateMode] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [newPublic, setNewPublic] = useState(false);

  useEffect(() => {
    if (open && destinations.length > 0 && (!destinationId || !destinations.some((playlist) => playlist.id === destinationId))) {
      setDestinationId(destinations[0].id);
    }
  }, [open, destinationId, destinations]);

  useEffect(() => {
    if (!open || !destinationId || selectedUris.length === 0) {
      setDuplicates(null);
      return;
    }
    let cancelled = false;
    setChecking(true);
    detectDuplicates({
      source_playlist_id: sourcePlaylistId,
      destination_playlist_id: destinationId,
      track_uris: selectedUris,
      skip_duplicates: skipDuplicates,
    })
      .then((summary) => {
        if (!cancelled) {
          setDuplicates(summary);
        }
      })
      .catch((err) => notify('error', errorMessage(err)))
      .finally(() => {
        if (!cancelled) {
          setChecking(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [open, destinationId, selectedUris.join('|'), skipDuplicates, sourcePlaylistId, notify]);

  async function handleCreatePlaylist() {
    if (!newName.trim()) {
      notify('error', 'Playlist name is required.');
      return;
    }
    setBusy(true);
    try {
      const playlist = await createPlaylist({ name: newName.trim(), description: newDescription, public: newPublic });
      onPlaylistCreated(playlist);
      setDestinationId(playlist.id);
      setCreateMode(false);
      setNewName('');
      setNewDescription('');
      setNewPublic(false);
      notify('success', `Created ${playlist.name}.`);
    } catch (err) {
      notify('error', errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleTransfer(action: 'copy' | 'move') {
    if (!destinationId) {
      notify('error', 'Choose a destination playlist.');
      return;
    }
    setBusy(true);
    setProgress(12);
    const timer = window.setInterval(() => setProgress((value) => Math.min(92, value + 8)), 400);
    try {
      const result = await transferTracks(action, {
        source_playlist_id: sourcePlaylistId,
        destination_playlist_id: destinationId,
        track_uris: selectedUris,
        skip_duplicates: skipDuplicates,
      });
      setProgress(100);
      notify('success', `${action === 'copy' ? 'Copied' : 'Moved'} ${result.transferred} tracks.`);
      onCompleted(result);
      onClose();
    } catch (err) {
      notify('error', errorMessage(err));
    } finally {
      window.clearInterval(timer);
      setBusy(false);
    }
  }

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/70 p-4">
      <section className="w-full max-w-2xl rounded-md border border-line bg-panel shadow-soft">
        <header className="flex items-center justify-between border-b border-line px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold text-white">Transfer selected tracks</h2>
            <p className="text-sm text-slate-400">{selectedUris.length.toLocaleString()} tracks selected</p>
          </div>
          <button className="rounded p-2 text-slate-400 hover:bg-white/10 hover:text-white" type="button" onClick={onClose} aria-label="Close transfer modal">
            <X className="h-5 w-5" />
          </button>
        </header>

        <div className="space-y-5 px-5 py-5">
          <div>
            <label className="text-sm font-medium text-slate-200" htmlFor="destination">
              Destination playlist
            </label>
            <select
              className="mt-2 h-11 w-full rounded-md border border-line bg-ink px-3 text-sm text-white"
              id="destination"
              value={destinationId}
              onChange={(event) => setDestinationId(event.target.value)}
            >
              {destinations.map((playlist) => (
                <option key={playlist.id} value={playlist.id}>
                  {playlist.name}
                </option>
              ))}
            </select>
          </div>

          <button
            className="inline-flex h-10 items-center gap-2 rounded-md border border-line px-3 text-sm text-slate-200 hover:bg-white/5"
            type="button"
            onClick={() => setCreateMode((value) => !value)}
          >
            <Plus className="h-4 w-4" />
            Create new playlist
          </button>

          {createMode ? (
            <div className="grid gap-3 rounded-md border border-line p-4">
              <input
                className="h-10 rounded-md border border-line bg-ink px-3 text-sm text-white"
                placeholder="Playlist name"
                value={newName}
                onChange={(event) => setNewName(event.target.value)}
              />
              <textarea
                className="min-h-20 rounded-md border border-line bg-ink px-3 py-2 text-sm text-white"
                placeholder="Description"
                value={newDescription}
                onChange={(event) => setNewDescription(event.target.value)}
              />
              <label className="flex items-center gap-2 text-sm text-slate-300">
                <input checked={newPublic} className="accent-spotify" type="checkbox" onChange={(event) => setNewPublic(event.target.checked)} />
                Public playlist
              </label>
              <button
                className="inline-flex h-10 w-fit items-center gap-2 rounded-md bg-spotify px-4 text-sm font-semibold text-black hover:bg-[#22D363]"
                type="button"
                onClick={() => void handleCreatePlaylist()}
                disabled={busy}
              >
                {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
                Create and use
              </button>
            </div>
          ) : null}

          <div className="rounded-md border border-line p-4">
            <label className="flex items-center gap-2 text-sm text-slate-200">
              <input checked={skipDuplicates} className="accent-spotify" type="checkbox" onChange={(event) => setSkipDuplicates(event.target.checked)} />
              Skip duplicates
            </label>
            <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
              <div className="rounded bg-ink p-3">
                <p className="text-slate-500">Duplicates</p>
                <p className="mt-1 text-xl font-semibold text-white">{checking ? '...' : duplicates?.duplicates ?? 0}</p>
              </div>
              <div className="rounded bg-ink p-3">
                <p className="text-slate-500">New tracks</p>
                <p className="mt-1 text-xl font-semibold text-white">{checking ? '...' : duplicates?.new_tracks ?? selectedUris.length}</p>
              </div>
            </div>
          </div>

          {busy ? <ProgressBar value={progress} /> : null}
        </div>

        <footer className="flex flex-col gap-3 border-t border-line px-5 py-4 sm:flex-row sm:justify-end">
          <button className="h-11 rounded-md border border-line px-4 text-sm text-slate-200 hover:bg-white/5" type="button" onClick={onClose}>
            Cancel
          </button>
          <button
            className="h-11 rounded-md border border-line px-4 text-sm font-semibold text-white hover:bg-white/5 disabled:opacity-50"
            type="button"
            disabled={busy || selectedUris.length === 0}
            onClick={() => void handleTransfer('copy')}
          >
            Copy Selected Songs
          </button>
          <button
            className="h-11 rounded-md bg-spotify px-4 text-sm font-semibold text-black hover:bg-[#22D363] disabled:opacity-50"
            type="button"
            disabled={busy || selectedUris.length === 0}
            onClick={() => void handleTransfer('move')}
          >
            Move Selected Songs
          </button>
        </footer>
      </section>
    </div>
  );
}
