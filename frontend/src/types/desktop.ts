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

export interface VirusTotalSettings {
  configured: boolean;
  apiKeyHint: string;
  enabled: boolean;
  uploadUnknown: boolean;
}

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
  pause_scan(): Promise<ApiResponse<{ status: string }>>;
  resume_scan(): Promise<ApiResponse<{ status: string }>>;
  stop_scan(): Promise<ApiResponse<{ status: string }>>;
  get_privilege_status(): Promise<ApiResponse<{ isAdmin: boolean }>>;
  get_quarantine_files(): Promise<ApiResponse<QuarantinedFile[]>>;
  quarantine_file(filepath: string, threatName: string): Promise<ApiResponse<{ quarantined: boolean }>>;
  restore_quarantine_file(filepath: string): Promise<ApiResponse<{ restored: boolean }>>;
  delete_quarantine_file(filepath: string): Promise<ApiResponse<{ deleted: boolean }>>;
  get_virustotal_settings(): Promise<ApiResponse<VirusTotalSettings>>;
  test_save_virustotal_key(
    apiKey: string,
    enabled: boolean,
    uploadUnknown: boolean,
  ): Promise<ApiResponse<VirusTotalSettings & { message: string }>>;
  set_virustotal_options(
    enabled: boolean,
    uploadUnknown: boolean,
  ): Promise<ApiResponse<VirusTotalSettings>>;
  start_native_drag(): Promise<void>;
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
