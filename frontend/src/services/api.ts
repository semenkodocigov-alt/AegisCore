import { ApiResponse } from '../types/api';
import { AuthResponse, LoginPayload, ProfileUpdatePayload, RegisterPayload, User } from '../types/auth';
import { NativeFileScanResult, QuarantinedFile, ScanProgress, SystemHealth } from '../types/scanner';
import { storageService } from './storage';
import { DesktopApi } from '../types/desktop';

const API_BASE = '/api';

class ApiService {
  private async getDesktopApi(): Promise<DesktopApi | undefined> {
    if (window.pywebview?.api) return window.pywebview.api;
    if (window.location.protocol !== 'file:') return undefined;

    await new Promise<void>((resolve) => {
      const timeout = window.setTimeout(resolve, 10000);
      window.addEventListener('pywebviewready', () => {
        window.clearTimeout(timeout);
        resolve();
      }, { once: true });
    });
    return window.pywebview?.api;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    const headers = new Headers(options.headers);
    headers.set('Content-Type', 'application/json');
    const token = storageService.getToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
      const data = await response.json().catch(() => null) as ApiResponse<T> | null;
      if (!response.ok) {
        return {
          success: false,
          error: data?.error || {
            code: `HTTP_${response.status}`,
            message: response.statusText || 'The request could not be completed.',
          },
          timestamp: Date.now(),
        };
      }
      if (!data) {
        return {
          success: false,
          error: { code: 'INVALID_RESPONSE', message: 'The service returned an empty response.' },
          timestamp: Date.now(),
        };
      }
      return data;
    } catch (error) {
      console.warn(`[Aegis API] Request to ${endpoint} failed.`, error);
      return {
        success: false,
        error: {
          code: endpoint.startsWith('/auth/') ? 'AUTH_API_UNAVAILABLE' : 'API_UNAVAILABLE',
          message: endpoint.startsWith('/auth/')
            ? 'The account service is unavailable. Restart Aegis Core and try again.'
            : `The ${endpoint} service is unavailable.`,
        },
        timestamp: Date.now(),
      };
    }
  }

  async login(payload: LoginPayload): Promise<ApiResponse<AuthResponse>> {
    const nativeApi = await this.getDesktopApi();
    if (nativeApi) return nativeApi.login(payload);
    return this.request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async register(payload: RegisterPayload): Promise<ApiResponse<AuthResponse>> {
    const nativeApi = await this.getDesktopApi();
    if (nativeApi) return nativeApi.register(payload);
    return this.request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  async getCurrentUser(): Promise<ApiResponse<User>> {
    const nativeApi = await this.getDesktopApi();
    if (nativeApi) {
      const token = storageService.getToken();
      return token
        ? nativeApi.get_current_user(token)
        : { success: false, error: { code: 'UNAUTHORIZED', message: 'No active session.' }, timestamp: Date.now() };
    }
    return this.request<User>('/auth/me', { method: 'GET' });
  }

  async updateCurrentUser(payload: ProfileUpdatePayload): Promise<ApiResponse<User>> {
    const nativeApi = await this.getDesktopApi();
    if (nativeApi) {
      const token = storageService.getToken();
      return token
        ? nativeApi.update_profile(token, payload)
        : { success: false, error: { code: 'UNAUTHORIZED', message: 'No active session.' }, timestamp: Date.now() };
    }
    return this.request<User>('/auth/me', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  }

  async logout(): Promise<ApiResponse<{ message: string }>> {
    const nativeApi = await this.getDesktopApi();
    if (nativeApi) return nativeApi.logout();
    return this.request<{ message: string }>('/auth/logout', { method: 'POST' });
  }

  async scanFile(filepath: string): Promise<ApiResponse<NativeFileScanResult>> {
    const nativeApi = await this.getDesktopApi();
    if (!nativeApi) {
      return {
        success: false,
        error: { code: 'DESKTOP_ONLY', message: 'File scanning is available in the Aegis Core desktop app.' },
        timestamp: Date.now(),
      };
    }
    return nativeApi.scan_file(filepath);
  }

  async selectScanTarget(): Promise<ApiResponse<{ targetPath: string }>> {
    const nativeApi = await this.getDesktopApi();
    if (!nativeApi) {
      return {
        success: false,
        error: { code: 'DESKTOP_ONLY', message: 'File selection is available in the Aegis Core desktop app.' },
        timestamp: Date.now(),
      };
    }
    return nativeApi.select_scan_target();
  }

  async startScan(
    type: 'quick' | 'full' | 'custom',
    targetPath?: string,
  ): Promise<ApiResponse<{ scanId: string; status: string }>> {
    const nativeApi = await this.getDesktopApi();
    if (nativeApi) return nativeApi.start_scan(type, targetPath);
    return this.request<{ scanId: string; status: string }>('/scan/start', {
      method: 'POST',
      body: JSON.stringify({ type, targetPath }),
    });
  }

  async getScanStatus(): Promise<ApiResponse<ScanProgress>> {
    const nativeApi = await this.getDesktopApi();
    if (nativeApi) return nativeApi.get_scan_status();
    return this.request<ScanProgress>('/scan/status', { method: 'GET' });
  }

  async stopScan(): Promise<ApiResponse<{ status: string }>> {
    const nativeApi = await this.getDesktopApi();
    if (nativeApi) return nativeApi.stop_scan();
    return this.request<{ status: string }>('/scan/stop', { method: 'POST' });
  }

  async getQuarantineFiles(): Promise<ApiResponse<QuarantinedFile[]>> {
    const nativeApi = await this.getDesktopApi();
    if (nativeApi) return nativeApi.get_quarantine_files();
    return this.request<QuarantinedFile[]>('/quarantine', { method: 'GET' });
  }

  async quarantineFile(filepath: string, threatName: string): Promise<ApiResponse<{ quarantined: boolean }>> {
    const nativeApi = await this.getDesktopApi();
    if (!nativeApi) {
      return {
        success: false,
        error: { code: 'DESKTOP_ONLY', message: 'Quarantine actions are available in the desktop app.' },
        timestamp: Date.now(),
      };
    }
    return nativeApi.quarantine_file(filepath, threatName);
  }

  async restoreQuarantineFile(fileId: string): Promise<ApiResponse<{ restored: boolean }>> {
    const nativeApi = await this.getDesktopApi();
    if (nativeApi) return nativeApi.restore_quarantine_file(fileId);
    return this.request<{ restored: boolean }>(`/quarantine/${fileId}/restore`, { method: 'POST' });
  }

  async deleteQuarantineFile(fileId: string): Promise<ApiResponse<{ deleted: boolean }>> {
    const nativeApi = await this.getDesktopApi();
    if (nativeApi) return nativeApi.delete_quarantine_file(fileId);
    return this.request<{ deleted: boolean }>(`/quarantine/${fileId}`, { method: 'DELETE' });
  }

  async getSystemHealth(): Promise<ApiResponse<SystemHealth>> {
    return this.request<SystemHealth>('/system/health', { method: 'GET' });
  }

  async toggleRealtimeProtection(enabled: boolean): Promise<ApiResponse<{ enabled: boolean }>> {
    return this.request<{ enabled: boolean }>('/system/realtime-protection', {
      method: 'POST',
      body: JSON.stringify({ enabled }),
    });
  }

}

export const apiService = new ApiService();
