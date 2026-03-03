'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '@/lib/api';

interface AuthContextValue {
  /** True when a valid token is stored */
  authenticated: boolean;
  /** Username (principal) of the logged-in user */
  username: string | null;
  /** Roles from the JWT */
  roles: string[];
  /** True while verifying token on mount */
  loading: boolean;
  /** Login with username/password, stores JWT */
  login: (username: string, password: string) => Promise<void>;
  /** Clear token and redirect to login */
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  authenticated: false,
  username: null,
  roles: [],
  loading: true,
  login: async () => {},
  logout: () => {},
});

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [username, setUsername] = useState<string | null>(null);
  const [roles, setRoles] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    localStorage.removeItem('autoforge_token');
    setAuthenticated(false);
    setUsername(null);
    setRoles([]);
  }, []);

  // Verify existing token on mount
  useEffect(() => {
    const token = localStorage.getItem('autoforge_token');
    if (!token) {
      setLoading(false);
      return;
    }

    api
      .getAuthInfo()
      .then((info) => {
        if (info.authenticated) {
          setAuthenticated(true);
          setUsername(info.principal);
          setRoles(info.roles || []);
        } else {
          logout();
        }
      })
      .catch(() => {
        // Token invalid/expired — clear it
        logout();
      })
      .finally(() => setLoading(false));
  }, [logout]);

  // Listen for forced logout (401 from fetchAPI)
  useEffect(() => {
    const handler = () => logout();
    window.addEventListener('autoforge:logout', handler);
    return () => window.removeEventListener('autoforge:logout', handler);
  }, [logout]);

  const login = useCallback(async (user: string, pass: string) => {
    const resp = await api.login(user, pass);
    localStorage.setItem('autoforge_token', resp.access_token);
    setAuthenticated(true);
    setUsername(user);
    setRoles(resp.roles || []);
  }, []);

  return (
    <AuthContext.Provider value={{ authenticated, username, roles, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
