import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { API_BASE_URL, errorMessage, setCsrfToken } from '../api/client';
import { getMe, logout as logoutRequest } from '../api/spotify';
import type { UserProfile } from '../types';

type AuthContextValue = {
  user: UserProfile | null;
  loading: boolean;
  error: string | null;
  loginUrl: string;
  refreshMe: () => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

let authRefreshCount = 0;
let authEffectCount = 0;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const loginUrl = `${API_BASE_URL}/api/auth/login`;

  const refreshMe = useCallback(async () => {
    authRefreshCount += 1;
    console.log(`[AuthContext] refreshMe #${authRefreshCount} invoked`);
    setLoading(true);
    setError(null);
    try {
      const profile = await getMe();
      setUser(profile);
      setCsrfToken(profile.csrf_token);
    } catch (err) {
      setUser(null);
      setCsrfToken(null);
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    await logoutRequest();
    setUser(null);
    setCsrfToken(null);
  }, []);

  useEffect(() => {
    authEffectCount += 1;
    console.log(`[AuthContext] useEffect #${authEffectCount} -> refreshMe`);
    void refreshMe();
  }, [refreshMe]);

  const value = useMemo(
    () => ({ user, loading, error, loginUrl, refreshMe, logout }),
    [user, loading, error, loginUrl, refreshMe, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return context;
}
