export type Image = {
  url: string;
  width?: number | null;
  height?: number | null;
};

export type UserProfile = {
  id: string;
  display_name: string | null;
  images: Image[];
  total_playlists: number;
  csrf_token: string;
};

export type PlaylistSummary = {
  id: string;
  name: string;
  images: Image[];
  owner: string;
  owner_id?: string | null;
  tracks_total: number;
  public?: boolean | null;
  collaborative: boolean;
  tracks_readable: boolean;
};

export type Track = {
  id: string | null;
  uri: string;
  name: string;
  artists: string[];
  album: string;
  album_art: string | null;
  duration_ms: number;
  added_at: string | null;
};

export type TrackPage = {
  playlist_id: string;
  tracks: Track[];
  total: number;
  offset: number;
  limit: number;
  next_offset: number | null;
  has_more: boolean;
  artists: string[];
  albums: string[];
};

export type DuplicateSummary = {
  duplicates: number;
  new_tracks: number;
  duplicate_uris: string[];
};

export type TransferResult = {
  operation_id: string;
  action: 'copy' | 'move';
  requested: number;
  transferred: number;
  skipped_duplicates: number;
  failures: string[];
  duplicate_summary: DuplicateSummary;
};

export type CreatePlaylistPayload = {
  name: string;
  description: string;
  public: boolean;
};
