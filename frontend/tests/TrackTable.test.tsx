import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { TrackTable } from '../src/components/TrackTable';
import type { Track } from '../src/types';

const tracks: Track[] = [
  {
    id: '1',
    uri: 'spotify:track:1',
    name: 'Song One',
    artists: ['Artist A'],
    album: 'Album A',
    album_art: null,
    duration_ms: 180000,
    added_at: '2026-01-01T00:00:00Z',
  },
];

describe('TrackTable', () => {
  it('renders tracks and toggles selection', async () => {
    const onToggle = vi.fn();
    render(
      <TrackTable
        tracks={tracks}
        selectedUris={new Set()}
        sortBy="name"
        sortOrder="asc"
        onToggle={onToggle}
        onToggleAllVisible={vi.fn()}
        onSort={vi.fn()}
      />,
    );

    expect(screen.getByText('Song One')).toBeInTheDocument();
    await userEvent.click(screen.getByLabelText('Select Song One'));

    expect(onToggle).toHaveBeenCalledWith('spotify:track:1');
  });
});
