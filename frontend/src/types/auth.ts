export interface User {
  id: string;
  email: string;
  nickname: string;
  avatarUrl?: string;
  role: 'admin' | 'user' | 'analyst' | 'guest';
  isGuest?: boolean;
  createdAt: string;
  lastLoginAt: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken?: string;
  expiresIn: number;
}

export interface AuthResponse {
  user: User;
  tokens: AuthTokens;
  message?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
  rememberMe: boolean;
}

export interface RegisterPayload {
  email: string;
  password: string;
  confirmPassword?: string;
  nickname: string;
  rememberMe: boolean;
}

export interface ProfileUpdatePayload {
  nickname?: string;
  email?: string;
  currentPassword?: string;
  newPassword?: string;
}

export interface UpgradeGuestPayload {
  email: string;
  password: string;
  nickname: string;
  rememberMe: boolean;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isGuest: boolean;
  isLoading: boolean;
  token: string | null;
  error: string | null;
}
