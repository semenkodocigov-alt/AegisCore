export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, string[] | string>;
}

export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: ApiError;
  timestamp: number;
}
