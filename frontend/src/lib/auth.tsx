"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { ReactNode } from "react";
import { ApiError, api } from "@/lib/api";
import type { User } from "@/types";

const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshSession: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function setStoredTokens(accessToken: string, refreshToken: string) {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

function clearStoredTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

function getStoredRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

async function fetchCurrentUser() {
  return api.get<User>("/auth/me");
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    clearStoredTokens();
    setUser(null);
  }, []);

  const refreshSession = useCallback(async () => {
    const refreshToken = getStoredRefreshToken();
    if (!refreshToken) {
      return false;
    }

    try {
      const tokenResponse = await api.post<TokenResponse>("/auth/refresh", {
        refresh_token: refreshToken,
      });
      setStoredTokens(tokenResponse.access_token, tokenResponse.refresh_token);
      const currentUser = await fetchCurrentUser();
      setUser(currentUser);
      return true;
    } catch (error) {
      console.error("Failed to refresh session:", error);
      logout();
      return false;
    }
  }, [logout]);

  useEffect(() => {
    async function restoreSession() {
      const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
      if (!accessToken) {
        setIsLoading(false);
        return;
      }

      try {
        const currentUser = await fetchCurrentUser();
        setUser(currentUser);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          await refreshSession();
        } else {
          logout();
        }
      } finally {
        setIsLoading(false);
      }
    }

    void restoreSession();
  }, [logout, refreshSession]);

  const login = useCallback(async (email: string, password: string) => {
    try {
      const tokenResponse = await api.post<TokenResponse>("/auth/login", {
        email,
        password,
      });
      setStoredTokens(tokenResponse.access_token, tokenResponse.refresh_token);
      const currentUser = await fetchCurrentUser();
      setUser(currentUser);
    } catch (error) {
      clearStoredTokens();
      setUser(null);
      throw error;
    }
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: user !== null,
      isLoading,
      login,
      logout,
      refreshSession,
    }),
    [isLoading, login, logout, refreshSession, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
