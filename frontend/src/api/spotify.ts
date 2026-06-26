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

export async function getMe(): Promise<UserProfile> {
  const { data } = await api.get<UserProfile>('/api/me');
  return data;
}

export async function getPlaylists(): Promise<PlaylistSummary[]> {
  const { data } = await api.get<PlaylistSummary[]>('/api/playlists');
  return data;
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
