/**
 * Storage service with secure persistence for Aegis Core
 * Supports persistent 'Remember Me' (localStorage), session-only (sessionStorage), and Guest mode
 */
import { User } from '../types/auth';

const TOKEN_KEY = 'aegis_access_token';
const REFRESH_KEY = 'aegis_refresh_token';
const USER_KEY = 'aegis_user_profile';
const REMEMBER_KEY = 'aegis_remember_pref';
const GUEST_KEY = 'aegis_guest_mode';

export const storageService = {
  getRememberMe(): boolean {
    return localStorage.getItem(REMEMBER_KEY) === 'true';
  },

  setRememberMe(value: boolean): void {
    localStorage.setItem(REMEMBER_KEY, value ? 'true' : 'false');
  },

  isGuest(): boolean {
    return localStorage.getItem(GUEST_KEY) === 'true' || sessionStorage.getItem(GUEST_KEY) === 'true';
  },

  setGuestSession(remember: boolean = false): User {
    const target = remember ? localStorage : sessionStorage;
    const now = new Date().toISOString();
    const guestUser: User = {
      id: `guest_${Math.random().toString(36).substring(2, 9)}`,
      email: 'guest@aegis.local',
      nickname: 'Guest',
      role: 'guest',
      isGuest: true,
      createdAt: now,
      lastLoginAt: now,
    };
    target.setItem(GUEST_KEY, 'true');
    this.setUser(guestUser, remember);
    this.setRememberMe(remember);
    return guestUser;
  },

  clearGuestSession(): void {
    localStorage.removeItem(GUEST_KEY);
    sessionStorage.removeItem(GUEST_KEY);
  },

  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
  },

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_KEY) || sessionStorage.getItem(REFRESH_KEY);
  },

  setTokens(accessToken: string, refreshToken?: string, remember: boolean = true): void {
    this.clearGuestSession();
    this.setRememberMe(remember);
    const targetStorage = remember ? localStorage : sessionStorage;
    const otherStorage = remember ? sessionStorage : localStorage;

    otherStorage.removeItem(TOKEN_KEY);
    otherStorage.removeItem(REFRESH_KEY);

    targetStorage.setItem(TOKEN_KEY, accessToken);
    if (refreshToken) {
      targetStorage.setItem(REFRESH_KEY, refreshToken);
    }
  },

  getUser<T = User>(): T | null {
    const raw = localStorage.getItem(USER_KEY) || sessionStorage.getItem(USER_KEY);
    if (!raw) return null;
    try {
      return JSON.parse(raw);
    } catch {
      return null;
    }
  },

  setUser(user: User, remember: boolean = true): void {
    const targetStorage = remember ? localStorage : sessionStorage;
    const otherStorage = remember ? sessionStorage : localStorage;
    otherStorage.removeItem(USER_KEY);
    targetStorage.setItem(USER_KEY, JSON.stringify(user));
  },

  clearAuth(): void {
    this.clearGuestSession();
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
    sessionStorage.removeItem(USER_KEY);
  },
};
