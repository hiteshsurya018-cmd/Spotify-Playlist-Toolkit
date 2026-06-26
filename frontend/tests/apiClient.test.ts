import { describe, expect, it } from 'vitest';

describe('api client', () => {
  it('uses the current page host for the default backend URL', async () => {
    const { defaultApiBaseUrl } = await import('../src/api/client');

    expect(defaultApiBaseUrl({ protocol: 'http:', hostname: '127.0.0.1' })).toBe('http://127.0.0.1:8000');
  });
});
