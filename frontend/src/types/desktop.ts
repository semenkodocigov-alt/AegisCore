import { ApiResponse } from './api';
import {
  AuthResponse,
  LoginPayload,
  ProfileUpdatePayload,
  RegisterPayload,
  User,
} from './auth';
import {
  NativeFileScanResult,
  QuarantinedFile,
  ScanProgress,
  ScanType,
} from './scanner';

export interface DesktopApi {
  login(payload: LoginPayload): Promise<ApiResponse<AuthResponse>>;
  register(payload: RegisterPayload): Promise<ApiResponse<AuthResponse>>;
  get_current_user(accessToken: string): Promise<ApiResponse<User>>;
  update_profile(
    accessToken: string,
    payload: ProfileUpdatePayload,
  ): Promise<ApiResponse<User>>;
  logout(): Promise<ApiResponse<{ message: string }>>;
  scan_file(filepath: string): Promise<ApiResponse<NativeFileScanResult>>;
  select_scan_target(): Promise<ApiResponse<{ targetPath: string }>>;
  start_scan(scanType: ScanType, targetPath?: string): Promise<ApiResponse<{ scanId: string; status: string }>>;
  get_scan_status(): Promise<ApiResponse<ScanProgress>>;
  stop_scan(): Promise<ApiResponse<{ status: string }>>;
  get_quarantine_files(): Promise<ApiResponse<QuarantinedFile[]>>;
  quarantine_file(filepath: string, threatName: string): Promise<ApiResponse<{ quarantined: boolean }>>;
  restore_quarantine_file(filepath: string): Promise<ApiResponse<{ restored: boolean }>>;
  delete_quarantine_file(filepath: string): Promise<ApiResponse<{ deleted: boolean }>>;
  minimize(): void;
  toggle_maximize(): void;
  close(): void;
}

declare global {
  interface Window {
    pywebview?: {
      api?: DesktopApi;
    };
  }
}
