import axios, { AxiosHeaders } from 'axios';

export function defaultApiBaseUrl(location?: Pick<Location, 'hostname' | 'protocol'>): string {
  if (!location) {
    return 'http://localhost:8000';
  }

  return `${location.protocol}//${location.hostname}:8000`;
}

const fallbackApiBaseUrl = defaultApiBaseUrl(typeof window === 'undefined' ? undefined : window.location);

export const API_BASE_URL = import.meta.env.VITE_API_URL ?? fallbackApiBaseUrl;

let csrfToken: string | null = null;
let playlistHttpRequestCount = 0;

export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  if ((config.method ?? 'get').toLowerCase() === 'get' && config.url === '/api/playlists') {
    playlistHttpRequestCount += 1;
    console.log(`[api.client] HTTP GET /api/playlists #${playlistHttpRequestCount}`, {
      baseURL: config.baseURL,
      url: config.url,
    });
  }

  if (csrfToken && ['post', 'put', 'patch', 'delete'].includes((config.method ?? '').toLowerCase())) {
    config.headers = AxiosHeaders.from(config.headers);
    config.headers.set('X-CSRF-Token', csrfToken);
  }
  return config;
});

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.error?.message ?? error.message;
  }
  return 'Unexpected error';
}

export function errorCode(error: unknown): string | undefined {
  if (axios.isAxiosError(error)) {
    return error.response?.data?.error?.code;
  }
  return undefined;
}
