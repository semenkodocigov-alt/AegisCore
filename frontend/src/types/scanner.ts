export type ScanType = 'quick' | 'full' | 'custom';

export type ThreatSeverity = 'clean' | 'low' | 'medium' | 'high' | 'critical';

export interface ThreatItem {
  id: string;
  filePath: string;
  fileName: string;
  threatName: string;
  severity: ThreatSeverity;
  score: number;
  detectedBy: string[];
  details: string[];
  hashes: {
    md5: string;
    sha1: string;
    sha256: string;
  };
  timestamp: number;
  quarantined: boolean;
}

export interface ScanProgress {
  status: 'idle' | 'scanning' | 'paused' | 'completed' | 'cancelled' | 'error';
  scanType: ScanType;
  currentPath: string;
  filesScanned: number;
  totalFiles: number;
  percentage: number;
  threatsFound: number;
  threats: ThreatItem[];
  elapsedSeconds: number;
  error?: string;
}

export interface QuarantinedFile {
  id: string;
  originalPath: string;
  originalName: string;
  quarantineName: string;
  threatName: string;
  size: number;
  timestamp: number;
  quarantinedAt: string;
}

export interface SystemHealth {
  realTimeProtection: boolean;
  cloudSync: boolean;
  virusTotalEnabled: boolean;
  signaturesCount: number;
  lastUpdated: string;
  memoryUsageMb: number;
  cpuPercent: number;
}

export interface NativeFileScanResult {
  filepath: string;
  is_threat: boolean;
  threat_name: string;
  details: string[];
}
