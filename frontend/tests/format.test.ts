import { describe, expect, it } from 'vitest';

import { exportUrl, formatDuration } from '../src/utils/format';

describe('format utilities', () => {
  it('formats milliseconds as m:ss', () => {
    expect(formatDuration(185000)).toBe('3:05');
  });

  it('builds selected-track export URLs', () => {
    const url = exportUrl('http://localhost:8000', 'csv', 'playlist-1', ['spotify:track:1', 'spotify:track:2']);

    expect(url).toContain('/api/export/csv');
    expect(url).toContain('playlist_id=playlist-1');
    expect(url).toContain('spotify%3Atrack%3A1%2Cspotify%3Atrack%3A2');
  });
});
