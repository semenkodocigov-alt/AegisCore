import React, { createContext, useContext, useEffect, useState } from 'react';
import { apiService } from '../services/api';
import { storageService } from '../services/storage';
import {
  AuthState,
  LoginPayload,
  ProfileUpdatePayload,
  RegisterPayload,
  UpgradeGuestPayload,
  User,
} from '../types/auth';

type AuthResult = { success: boolean; error?: string };

interface AuthContextType extends AuthState {
  login: (payload: LoginPayload) => Promise<AuthResult>;
  register: (payload: RegisterPayload) => Promise<AuthResult>;
  continueAsGuest: (rememberMe?: boolean) => void;
  updateProfile: (payload: ProfileUpdatePayload) => Promise<AuthResult>;
  upgradeGuestAccount: (payload: UpgradeGuestPayload) => Promise<AuthResult>;
  logout: () => Promise<void>;
  clearError: () => void;
  rememberMePreference: boolean;
  setRememberMePreference: (value: boolean) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => storageService.getUser<User>());
  const [token, setToken] = useState<string | null>(() => storageService.getToken());
  const [isGuest, setIsGuest] = useState<boolean>(() => storageService.isGuest());
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rememberMePreference, setRememberMePreferenceState] = useState(
    () => storageService.getRememberMe(),
  );

  const setRememberMePreference = (value: boolean) => {
    setRememberMePreferenceState(value);
    storageService.setRememberMe(value);
  };

  useEffect(() => {
    let isMounted = true;

    const restoreSession = async () => {
      if (storageService.isGuest()) {
        const storedUser = storageService.getUser<User>();
        if (storedUser && isMounted) {
          setUser(storedUser);
          setIsGuest(true);
          setIsLoading(false);
          return;
        }
        storageService.clearAuth();
      }

      const storedToken = storageService.getToken();
      if (!storedToken) {
        if (isMounted) {
          setUser(null);
          setToken(null);
          setIsGuest(false);
          setIsLoading(false);
        }
        return;
      }

      try {
        const response = await apiService.getCurrentUser();
        if (!isMounted) return;
        if (response.success && response.data) {
          setUser(response.data);
          setToken(storedToken);
          setIsGuest(false);
        } else {
          storageService.clearAuth();
          setUser(null);
          setToken(null);
          setIsGuest(false);
          setError(response.error?.message || 'Your saved session is no longer valid. Please sign in again.');
        }
      } catch (restoreError) {
        if (isMounted) {
          storageService.clearAuth();
          setUser(null);
          setToken(null);
          setIsGuest(false);
          setError(
            restoreError instanceof Error
              ? `Could not restore your session: ${restoreError.message}`
              : 'Could not restore your session. Please sign in again.',
          );
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    void restoreSession();
    return () => {
      isMounted = false;
    };
  }, []);

  const login = async (payload: LoginPayload): Promise<AuthResult> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiService.login(payload);
      if (!response.success || !response.data) {
        const message = response.error?.message || 'Sign in failed. Check your details and try again.';
        setError(message);
        return { success: false, error: message };
      }

      const { user: authenticatedUser, tokens } = response.data;
      storageService.setTokens(tokens.accessToken, tokens.refreshToken, payload.rememberMe);
      storageService.setUser(authenticatedUser, payload.rememberMe);
      setUser(authenticatedUser);
      setToken(tokens.accessToken);
      setIsGuest(false);
      setRememberMePreference(payload.rememberMe);
      return { success: true };
    } catch (loginError) {
      const message = loginError instanceof Error ? loginError.message : 'Sign in could not be completed.';
      setError(message);
      return { success: false, error: message };
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (payload: RegisterPayload): Promise<AuthResult> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await apiService.register(payload);
      if (!response.success || !response.data) {
        const message = response.error?.message || 'Account creation failed. Check the details and try again.';
        setError(message);
        return { success: false, error: message };
      }

      const { user: authenticatedUser, tokens } = response.data;
      storageService.setTokens(tokens.accessToken, tokens.refreshToken, payload.rememberMe);
      storageService.setUser(authenticatedUser, payload.rememberMe);
      setUser(authenticatedUser);
      setToken(tokens.accessToken);
      setIsGuest(false);
      setRememberMePreference(payload.rememberMe);
      return { success: true };
    } catch (registrationError) {
      const message = registrationError instanceof Error
        ? registrationError.message
        : 'Account creation could not be completed.';
      setError(message);
      return { success: false, error: message };
    } finally {
      setIsLoading(false);
    }
  };

  const continueAsGuest = (rememberMe = false) => {
    storageService.clearAuth();
    const guestUser = storageService.setGuestSession(rememberMe);
    setUser(guestUser);
    setIsGuest(true);
    setToken(null);
    setRememberMePreferenceState(rememberMe);
    setError(null);
  };

  const updateProfile = async (payload: ProfileUpdatePayload): Promise<AuthResult> => {
    if (!user) return { success: false, error: 'There is no active session.' };
    setError(null);

    if (isGuest) {
      const updatedGuest: User = {
        ...user,
        nickname: payload.nickname?.trim() || user.nickname,
      };
      storageService.setUser(updatedGuest, rememberMePreference);
      setUser(updatedGuest);
      return { success: true };
    }

    setIsLoading(true);
    try {
      const response = await apiService.updateCurrentUser(payload);
      if (!response.success || !response.data) {
        const message = response.error?.message || 'Your profile could not be saved.';
        setError(message);
        return { success: false, error: message };
      }
      storageService.setUser(response.data, rememberMePreference);
      setUser(response.data);
      return { success: true };
    } catch (profileError) {
      const message = profileError instanceof Error
        ? profileError.message
        : 'Your profile could not be saved.';
      setError(message);
      return { success: false, error: message };
    } finally {
      setIsLoading(false);
    }
  };

  const upgradeGuestAccount = (payload: UpgradeGuestPayload): Promise<AuthResult> => register(payload);

  const logout = async () => {
    setIsLoading(true);
    setError(null);
    try {
      if (!isGuest) {
        const response = await apiService.logout();
        if (!response.success) setError(response.error?.message || 'The session could not be closed cleanly.');
      }
    } catch (logoutError) {
      setError(logoutError instanceof Error ? logoutError.message : 'The session could not be closed cleanly.');
    } finally {
      storageService.clearAuth();
      setUser(null);
      setToken(null);
      setIsGuest(false);
      setIsLoading(false);
    }
  };

  const clearError = () => setError(null);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isGuest,
        isLoading,
        token,
        error,
        login,
        register,
        continueAsGuest,
        updateProfile,
        upgradeGuestAccount,
        logout,
        clearError,
        rememberMePreference,
        setRememberMePreference,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
