import { api } from './client';
import type {
  CreatePlaylistPayload,
  DuplicateSummary,
  PlaylistSummary,
  TrackPage,
  TransferResult,
  UserProfile,
} from '../types';

export type TrackQuery = {
  playlistId: string;
  offset?: number;
  limit?: number;
  search?: string;
  artist?: string;
  album?: string;
  minDurationMs?: number;
  maxDurationMs?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
};

let meRequestCount = 0;
let playlistsRequestCount = 0;
let meRequest: Promise<UserProfile> | null = null;
let playlistsRequest: Promise<PlaylistSummary[]> | null = null;
let playlistsCache: { data: PlaylistSummary[]; expiresAt: number } | null = null;
let playlistsInvocationCount = 0;

const PLAYLIST_CACHE_MS = 60_000;

export async function getMe(): Promise<UserProfile> {
  if (meRequest) {
    console.log('[api.spotify] getMe -> using in-flight request');
    return meRequest;
  }

  meRequestCount += 1;
  console.log(`[api.spotify] getMe #${meRequestCount} -> GET /api/me`);
  meRequest = api
    .get<UserProfile>('/api/me')
    .then(({ data }) => data)
    .finally(() => {
      meRequest = null;
    });
  return meRequest;
}

export function invalidatePlaylistsCache(): void {
  playlistsCache = null;
  playlistsRequest = null;
}

export async function getPlaylists(options: { force?: boolean; source?: string } = {}): Promise<PlaylistSummary[]> {
  playlistsInvocationCount += 1;
  const source = options.source ?? 'unknown';
  console.log(`[api.spotify] getPlaylists invocation #${playlistsInvocationCount}`, {
    source,
    force: options.force ?? false,
    hasCache: Boolean(playlistsCache),
    cacheExpiresInMs: playlistsCache ? playlistsCache.expiresAt - Date.now() : null,
    hasInFlightRequest: Boolean(playlistsRequest),
  });

  if (!options.force && playlistsCache && playlistsCache.expiresAt > Date.now()) {
    console.log(`[api.spotify] getPlaylists -> using cached playlists source=${source}`);
    return playlistsCache.data;
  }

  if (!options.force && playlistsRequest) {
    console.log(`[api.spotify] getPlaylists -> using in-flight request source=${source}`);
    return playlistsRequest;
  }

  playlistsRequestCount += 1;
  console.log(`[api.spotify] getPlaylists network #${playlistsRequestCount} -> GET /api/playlists source=${source}`);
  playlistsRequest = api
    .get<PlaylistSummary[]>('/api/playlists')
    .then(({ data }) => {
      playlistsCache = {
        data,
        expiresAt: Date.now() + PLAYLIST_CACHE_MS,
      };
      return data;
    })
    .finally(() => {
      playlistsRequest = null;
    });
  return playlistsRequest;
}

export async function getTracks(query: TrackQuery): Promise<TrackPage> {
  const { data } = await api.get<TrackPage>(`/api/playlists/${query.playlistId}/tracks`, {
    params: {
      offset: query.offset ?? 0,
      limit: query.limit ?? 100,
      search: query.search || undefined,
      artist: query.artist || undefined,
      album: query.album || undefined,
      min_duration_ms: query.minDurationMs || undefined,
      max_duration_ms: query.maxDurationMs || undefined,
      sort_by: query.sortBy ?? 'added_at',
      sort_order: query.sortOrder ?? 'desc',
    },
  });
  return data;
}

export async function createPlaylist(payload: CreatePlaylistPayload): Promise<PlaylistSummary> {
  const { data } = await api.post<PlaylistSummary>('/api/playlists/create', payload);
  invalidatePlaylistsCache();
  return data;
}

export async function detectDuplicates(payload: {
  source_playlist_id: string;
  destination_playlist_id: string;
  track_uris: string[];
  skip_duplicates: boolean;
}): Promise<DuplicateSummary> {
  const { data } = await api.post<DuplicateSummary>('/api/tracks/duplicates', payload);
  return data;
}

export async function transferTracks(
  action: 'copy' | 'move',
  payload: {
    source_playlist_id: string;
    destination_playlist_id: string;
    track_uris: string[];
    skip_duplicates: boolean;
  },
): Promise<TransferResult> {
  const { data } = await api.post<TransferResult>(`/api/tracks/${action}`, payload);
  return data;
}

export async function undoTransfer(): Promise<{ restored: number; action: string; message: string }> {
  const { data } = await api.post('/api/tracks/undo');
  return data;
}

export async function logout(): Promise<void> {
  await api.post('/api/auth/logout');
}
