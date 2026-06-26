import { Download, Lock, RotateCcw, Search, SlidersHorizontal } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';

import { API_BASE_URL, errorCode, errorMessage } from '../api/client';
import { getPlaylists, getTracks, undoTransfer } from '../api/spotify';
import { TrackTable } from '../components/TrackTable';
import { TransferModal } from '../components/TransferModal';
import { useToast } from '../context/ToastContext';
import type { PlaylistSummary, Track, TransferResult } from '../types';
import { exportUrl, thirtyDaysAgo } from '../utils/format';

export function PlaylistManager() {
  const { playlistId = '' } = useParams();
  const { notify } = useToast();
  const [playlists, setPlaylists] = useState<PlaylistSummary[]>([]);
  const [tracks, setTracks] = useState<Track[]>([]);
  const [selectedUris, setSelectedUris] = useState<Set<string>>(new Set());
  const [search, setSearch] = useState('');
  const [artist, setArtist] = useState('');
  const [album, setAlbum] = useState('');
  const [minDuration, setMinDuration] = useState('');
  const [maxDuration, setMaxDuration] = useState('');
  const [sortBy, setSortBy] = useState('added_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [nextOffset, setNextOffset] = useState<number | null>(0);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [lastTransfer, setLastTransfer] = useState<TransferResult | null>(null);
  const [blockedPlaylistIds, setBlockedPlaylistIds] = useState<Set<string>>(new Set());

  const selectedPlaylist = playlists.find((playlist) => playlist.id === playlistId);
  const tracksUnavailable = selectedPlaylist?.tracks_readable === false;
  const artists = useMemo(() => [...new Set(tracks.flatMap((track) => track.artists))].sort(), [tracks]);
  const albums = useMemo(() => [...new Set(tracks.map((track) => track.album))].sort(), [tracks]);
  const selectedList = useMemo(() => [...selectedUris], [selectedUris]);

  const loadFirstPage = useCallback(async () => {
    setLoading(true);
    try {
      const playlistData = await getPlaylists();
      setPlaylists(playlistData);

      const playlist = playlistData.find((item) => item.id === playlistId);
      if (playlist && (!playlist.tracks_readable || blockedPlaylistIds.has(playlistId))) {
        setTracks([]);
        setSelectedUris(new Set());
        setNextOffset(null);
        setTotal(playlist.tracks_total);
        return;
      }

      const trackPage = await getTracks({
        playlistId,
        offset: 0,
        search,
        artist,
        album,
        minDurationMs: minDuration ? Number(minDuration) * 1000 : undefined,
        maxDurationMs: maxDuration ? Number(maxDuration) * 1000 : undefined,
        sortBy,
        sortOrder,
      });
      setTracks(trackPage.tracks);
      setNextOffset(trackPage.next_offset);
      setTotal(trackPage.total);
    } catch (err) {
      if (errorCode(err) === 'playlist_tracks_forbidden') {
        setBlockedPlaylistIds((current) => new Set([...current, playlistId]));
        setPlaylists((current) =>
          current.map((playlist) => (playlist.id === playlistId ? { ...playlist, tracks_readable: false } : playlist)),
        );
        setTracks([]);
        setSelectedUris(new Set());
        setNextOffset(null);
      }
      notify('error', errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [playlistId, search, artist, album, minDuration, maxDuration, sortBy, sortOrder, notify, blockedPlaylistIds]);

  useEffect(() => {
    void loadFirstPage();
  }, [loadFirstPage]);

  async function loadMore() {
    if (nextOffset === null || tracksUnavailable) {
      return;
    }
    setLoading(true);
    try {
      const page = await getTracks({
        playlistId,
        offset: nextOffset,
        search,
        artist,
        album,
        minDurationMs: minDuration ? Number(minDuration) * 1000 : undefined,
        maxDurationMs: maxDuration ? Number(maxDuration) * 1000 : undefined,
        sortBy,
        sortOrder,
      });
      setTracks((current) => [...current, ...page.tracks]);
      setNextOffset(page.next_offset);
      setTotal(page.total);
    } catch (err) {
      if (errorCode(err) === 'playlist_tracks_forbidden') {
        setBlockedPlaylistIds((current) => new Set([...current, playlistId]));
        setPlaylists((current) =>
          current.map((playlist) => (playlist.id === playlistId ? { ...playlist, tracks_readable: false } : playlist)),
        );
        setNextOffset(null);
      }
      notify('error', errorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  function toggle(uri: string) {
    setSelectedUris((current) => {
      const next = new Set(current);
      if (next.has(uri)) {
        next.delete(uri);
      } else {
        next.add(uri);
      }
      return next;
    });
  }

  function toggleAllVisible() {
    setSelectedUris((current) => {
      const next = new Set(current);
      const allSelected = tracks.length > 0 && tracks.every((track) => next.has(track.uri));
      tracks.forEach((track) => {
        if (allSelected) {
          next.delete(track.uri);
        } else {
          next.add(track.uri);
        }
      });
      return next;
    });
  }

  function updateSort(column: string) {
    if (sortBy === column) {
      setSortOrder((current) => (current === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
  }

  function selectByArtist() {
    if (!artist) {
      return;
    }
    setSelectedUris((current) => new Set([...current, ...tracks.filter((track) => track.artists.includes(artist)).map((track) => track.uri)]));
  }

  function selectByAlbum() {
    if (!album) {
      return;
    }
    setSelectedUris((current) => new Set([...current, ...tracks.filter((track) => track.album === album).map((track) => track.uri)]));
  }

  function selectDuplicateTracks() {
    const seen = new Map<string, string>();
    const duplicates: string[] = [];
    tracks.forEach((track) => {
      const key = `${track.name.toLowerCase()}|${track.artists.join(',').toLowerCase()}|${track.album.toLowerCase()}`;
      if (seen.has(key)) {
        duplicates.push(track.uri);
      } else {
        seen.set(key, track.uri);
      }
    });
    setSelectedUris((current) => new Set([...current, ...duplicates]));
  }

  function selectRecentlyAdded() {
    const threshold = thirtyDaysAgo();
    setSelectedUris(
      (current) =>
        new Set([
          ...current,
          ...tracks
            .filter((track) => track.added_at && new Date(track.added_at).getTime() >= threshold)
            .map((track) => track.uri),
        ]),
    );
  }

  async function handleUndo() {
    try {
      const result = await undoTransfer();
      notify('success', result.message);
      await loadFirstPage();
    } catch (err) {
      notify('error', errorMessage(err));
    }
  }

  function exportSelected(format: 'csv' | 'json') {
    if (selectedList.length === 0) {
      notify('error', 'Select tracks before exporting.');
      return;
    }
    window.open(exportUrl(API_BASE_URL, format, playlistId, selectedList), '_blank', 'noopener,noreferrer');
  }

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div className="min-w-0">
          <p className="text-sm uppercase tracking-wide text-spotify">Playlist Manager</p>
          <h1 className="mt-1 truncate text-3xl font-semibold text-white">{selectedPlaylist?.name ?? 'Selected playlist'}</h1>
          <p className="mt-1 text-sm text-slate-400">
            {tracks.length.toLocaleString()} loaded of {total.toLocaleString()} tracks
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button className="h-10 rounded-md border border-line px-3 text-sm text-slate-200 hover:bg-white/5" type="button" onClick={() => setSelectedUris(new Set())}>
            Deselect all
          </button>
          <button className="h-10 rounded-md border border-line px-3 text-sm text-slate-200 hover:bg-white/5" type="button" onClick={() => void handleUndo()}>
            <RotateCcw className="mr-2 inline h-4 w-4" />
            Undo Operation
          </button>
          <button className="h-10 rounded-md border border-line px-3 text-sm text-slate-200 hover:bg-white/5" type="button" onClick={() => exportSelected('csv')}>
            <Download className="mr-2 inline h-4 w-4" />
            CSV
          </button>
          <button className="h-10 rounded-md border border-line px-3 text-sm text-slate-200 hover:bg-white/5" type="button" onClick={() => exportSelected('json')}>
            JSON
          </button>
          <button
            className="h-10 rounded-md bg-spotify px-4 text-sm font-semibold text-black hover:bg-[#22D363] disabled:opacity-50"
            type="button"
            disabled={selectedUris.size === 0 || tracksUnavailable}
            onClick={() => setModalOpen(true)}
          >
            Transfer {selectedUris.size.toLocaleString()}
          </button>
        </div>
      </div>

      {tracksUnavailable ? (
        <div className="flex items-start gap-3 rounded-md border border-line bg-panel px-4 py-3 text-sm text-slate-200">
          <Lock className="mt-0.5 h-4 w-4 shrink-0 text-slate-500" />
          <p>
            Spotify only allows track access for playlists you own or collaborate on. This followed playlist can stay in
            your library, but it cannot be used as a source here.
          </p>
        </div>
      ) : null}

      <div className="grid gap-3 rounded-md border border-line bg-panel p-4 lg:grid-cols-[1.4fr_1fr_1fr_0.7fr_0.7fr]">
        <label className="relative block">
          <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-slate-500" />
          <input
            className="h-10 w-full rounded-md border border-line bg-ink pl-9 pr-3 text-sm text-white"
            placeholder="Search title, artist, or album"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </label>
        <select className="h-10 rounded-md border border-line bg-ink px-3 text-sm text-white" value={artist} onChange={(event) => setArtist(event.target.value)}>
          <option value="">All artists</option>
          {artists.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <select className="h-10 rounded-md border border-line bg-ink px-3 text-sm text-white" value={album} onChange={(event) => setAlbum(event.target.value)}>
          <option value="">All albums</option>
          {albums.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
        <input className="h-10 rounded-md border border-line bg-ink px-3 text-sm text-white" placeholder="Min sec" value={minDuration} onChange={(event) => setMinDuration(event.target.value)} />
        <input className="h-10 rounded-md border border-line bg-ink px-3 text-sm text-white" placeholder="Max sec" value={maxDuration} onChange={(event) => setMaxDuration(event.target.value)} />
      </div>

      <div className="flex flex-wrap gap-2">
        <button className="h-10 rounded-md border border-line px-3 text-sm text-slate-200 hover:bg-white/5" type="button" onClick={selectByArtist}>
          <SlidersHorizontal className="mr-2 inline h-4 w-4" />
          Select all songs by artist
        </button>
        <button className="h-10 rounded-md border border-line px-3 text-sm text-slate-200 hover:bg-white/5" type="button" onClick={selectByAlbum}>
          Select all songs from album
        </button>
        <button className="h-10 rounded-md border border-line px-3 text-sm text-slate-200 hover:bg-white/5" type="button" onClick={selectDuplicateTracks}>
          Select duplicate tracks
        </button>
        <button className="h-10 rounded-md border border-line px-3 text-sm text-slate-200 hover:bg-white/5" type="button" onClick={selectRecentlyAdded}>
          Select recently added tracks
        </button>
      </div>

      {lastTransfer ? (
        <div className="rounded-md border border-spotify/40 bg-spotify/10 px-4 py-3 text-sm text-slate-100">
          Last {lastTransfer.action}: {lastTransfer.transferred} transferred, {lastTransfer.skipped_duplicates} skipped duplicates.
        </div>
      ) : null}

      {tracksUnavailable ? null : (
        <TrackTable tracks={tracks} selectedUris={selectedUris} sortBy={sortBy} sortOrder={sortOrder} onToggle={toggle} onToggleAllVisible={toggleAllVisible} onSort={updateSort} />
      )}

      <div className="flex justify-center">
        <button
          className="h-11 rounded-md border border-line px-4 text-sm text-slate-200 hover:bg-white/5 disabled:opacity-50"
          type="button"
          disabled={loading || nextOffset === null}
          onClick={() => void loadMore()}
        >
          {loading ? 'Loading...' : nextOffset === null ? 'All tracks loaded' : 'Load more'}
        </button>
      </div>

      <TransferModal
        open={modalOpen}
        sourcePlaylistId={playlistId}
        playlists={playlists}
        selectedUris={selectedList}
        onClose={() => setModalOpen(false)}
        onPlaylistCreated={(playlist) => setPlaylists((current) => [playlist, ...current])}
        onCompleted={(result) => {
          setLastTransfer(result);
          setSelectedUris(new Set());
          void loadFirstPage();
        }}
      />
    </section>
  );
}
