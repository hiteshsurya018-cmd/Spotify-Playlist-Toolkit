export function formatDuration(durationMs: number): string {
  const totalSeconds = Math.round(durationMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

export function thirtyDaysAgo(): number {
  return Date.now() - 1000 * 60 * 60 * 24 * 30;
}

export function exportUrl(apiBaseUrl: string, format: 'csv' | 'json', playlistId: string, uris: string[]): string {
  const params = new URLSearchParams({ playlist_id: playlistId, track_uris: uris.join(',') });
  return `${apiBaseUrl}/api/export/${format}?${params.toString()}`;
}
