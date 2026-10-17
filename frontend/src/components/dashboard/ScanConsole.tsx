import React, { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { apiService } from '../../services/api';
import { ScanProgress, ScanType, ThreatItem } from '../../types/scanner';

interface ScanConsoleProps {
  onThreatQuarantined?: (threat: ThreatItem) => void;
}

const emptyScan: ScanProgress = {
  status: 'idle',
  scanType: 'quick',
  currentPath: '',
  filesScanned: 0,
  totalFiles: 0,
  percentage: 0,
  threatsFound: 0,
  threats: [],
  elapsedSeconds: 0,
};

const scanOptions: { type: ScanType; title: string; description: string; detail: string }[] = [
  {
    type: 'quick',
    title: 'Quick scan',
    description: 'Temporary files, Downloads, and Desktop folders.',
    detail: 'A short check of common file locations',
  },
  {
    type: 'full',
    title: 'Extended scan',
    description: 'Your home folder and selected Windows system folders.',
    detail: 'A broader check, with a file-count limit',
  },
  {
    type: 'custom',
    title: 'Choose a file',
    description: 'Pick one file to inspect with the local scanner.',
    detail: 'You choose exactly what to check',
  },
];

export const ScanConsole: React.FC<ScanConsoleProps> = ({ onThreatQuarantined }) => {
  const [scan, setScan] = useState<ScanProgress>(emptyScan);
  const [scanError, setScanError] = useState('');
  const [startupMessage, setStartupMessage] = useState('');
  const [isStartupScanning, setIsStartupScanning] = useState(false);

  useEffect(() => {
    const targetPath = new URLSearchParams(window.location.search).get('scan');
    if (!targetPath) return;

    let isActive = true;
    setIsStartupScanning(true);
    void apiService.scanFile(targetPath).then((response) => {
      if (!isActive) return;
      if (!response.success || !response.data) {
        setScanError(response.error?.message || 'The selected file could not be scanned.');
        return;
      }
      setStartupMessage(
        response.data.is_threat
          ? `A potential threat was identified in ${response.data.filepath}: ${response.data.threat_name || 'unclassified file'}.`
          : `File check complete. No threat was identified in ${response.data.filepath}.`,
      );
    }).catch((error: unknown) => {
      if (isActive) {
        setScanError(error instanceof Error ? error.message : 'The selected file could not be scanned.');
      }
    }).finally(() => {
      if (isActive) setIsStartupScanning(false);
    });

    return () => {
      isActive = false;
    };
  }, []);

  useEffect(() => {
    if (scan.status !== 'scanning') return;
    let isActive = true;
    let timer: number | undefined;
    const refresh = async () => {
      try {
        const response = await apiService.getScanStatus();
        if (!isActive) return;
        if (!response.success || !response.data) {
          setScanError(response.error?.message || 'Scan progress is unavailable.');
          setScan((current) => ({ ...current, status: 'error' }));
          return;
        }
        setScan(response.data);
        if (response.data.status === 'error') {
          setScanError(response.data.error || 'The scan could not be completed.');
        }
      } catch (error) {
        if (!isActive) return;
        setScanError(error instanceof Error ? error.message : 'Scan progress is unavailable.');
        setScan((current) => ({ ...current, status: 'error' }));
      } finally {
        if (isActive) {
          timer = window.setTimeout(() => void refresh(), 750);
        }
      }
    };

    void refresh();
    return () => {
      isActive = false;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [scan.status]);

  const startScan = async (type: ScanType) => {
    setScanError('');
    setStartupMessage('');
    let targetPath: string | undefined;
    if (type === 'custom') {
      const selection = await apiService.selectScanTarget();
      if (!selection.success || !selection.data) {
        if (selection.error?.code !== 'SELECTION_CANCELLED') {
          setScanError(selection.error?.message || 'Choose a file to continue.');
        }
        return;
      }
      targetPath = selection.data.targetPath;
    }

    const response = await apiService.startScan(type, targetPath);
    if (!response.success) {
      setScanError(response.error?.message || 'The scan could not be started.');
      return;
    }
    setScan({
      ...emptyScan,
      status: 'scanning',
      scanType: type,
      currentPath: 'Preparing scan…',
    });
  };

  const stopScan = async () => {
    const response = await apiService.stopScan();
    if (!response.success) setScanError(response.error?.message || 'The scan could not be stopped.');
  };

  const quarantineThreat = async (threat: ThreatItem) => {
    const response = await apiService.quarantineFile(threat.filePath, threat.threatName);
    if (!response.success) {
      setScanError(response.error?.message || 'The file could not be moved to quarantine.');
      return;
    }
    setScan((current) => ({
      ...current,
      threats: current.threats.map((item) => item.id === threat.id ? { ...item, quarantined: true } : item),
    }));
    onThreatQuarantined?.(threat);
  };

  const isScanning = scan.status === 'scanning';

  return (
    <section className="scan-page">
      <header className="page-heading">
        <div>
          <p className="eyebrow">LOCAL FILE CHECKS</p>
          <h1>Scan files</h1>
          <p>Choose a scan. Your selected files are checked on this device.</p>
        </div>
        {scan.status === 'completed' && <span className="session-badge"><span />Last scan complete</span>}
      </header>

      {(scanError || startupMessage || isStartupScanning) && (
        <div className={`account-notice ${scanError ? 'account-notice-error' : ''}`} role={scanError ? 'alert' : 'status'}>
          {scanError || (isStartupScanning ? 'Checking the file passed to Aegis Core…' : startupMessage)}
        </div>
      )}

      {!isScanning && (
        <div className="scan-options">
          {scanOptions.map((option, index) => (
            <motion.article
              className="scan-option"
              key={option.type}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.045, duration: 0.2 }}
            >
              <span className="scan-option-index">0{index + 1}</span>
              <h2>{option.title}</h2>
              <p>{option.description}</p>
              <span className="scan-option-detail">{option.detail}</span>
              <motion.button
                className={`button ${option.type === 'custom' ? 'button-secondary' : 'button-primary'} scan-option-action`}
                type="button"
                onClick={() => void startScan(option.type)}
                whileTap={{ scale: 0.985 }}
                transition={{ type: 'spring', stiffness: 420, damping: 28 }}
              >
                {option.type === 'custom' ? 'Browse files' : 'Start scan'}
                <span aria-hidden="true">→</span>
              </motion.button>
            </motion.article>
          ))}
        </div>
      )}

      <AnimatePresence>
        {(isScanning || scan.status === 'completed' || scan.status === 'cancelled' || scan.status === 'error') && (
          <motion.section
            className="scan-progress-card"
            initial={{ opacity: 0, y: 7 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
          >
            <div className="scan-progress-heading">
              <div>
                <p className="eyebrow">{isScanning ? 'SCAN IN PROGRESS' : 'SCAN SUMMARY'}</p>
                <h2>
                  {isScanning ? 'Checking files' : scan.status === 'error' ? 'Scan stopped with an error' :
                    scan.status === 'cancelled' ? 'Scan cancelled' : 'Scan complete'}
                </h2>
              </div>
              {isScanning && (
                <button className="button button-secondary" type="button" onClick={() => void stopScan()}>
                  Stop scan
                </button>
              )}
            </div>

            <div className="scan-progress-track" role="progressbar" aria-valuenow={scan.percentage} aria-valuemin={0} aria-valuemax={100}>
              <motion.span animate={{ width: `${scan.percentage}%` }} transition={{ duration: 0.25 }} />
            </div>

            <div className="scan-metrics">
              <div><span>Progress</span><strong>{scan.percentage}%</strong></div>
              <div><span>Files checked</span><strong>{scan.filesScanned.toLocaleString()}</strong></div>
              <div><span>Findings</span><strong>{scan.threatsFound}</strong></div>
              <div><span>Elapsed</span><strong>{scan.elapsedSeconds}s</strong></div>
            </div>
            <p className="scan-current-path" title={scan.currentPath}>{scan.currentPath || 'Waiting for the first file…'}</p>
          </motion.section>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {scan.threats.length > 0 && (
          <motion.section
            className="account-card scan-findings"
            initial={{ opacity: 0, y: 7 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
          >
            <div className="card-heading">
              <div>
                <p className="eyebrow">REVIEW REQUIRED</p>
                <h2>{scan.threats.length} finding{scan.threats.length === 1 ? '' : 's'}</h2>
              </div>
            </div>
            <div className="findings-list">
              {scan.threats.map((threat) => (
                <div className="finding-row" key={threat.id}>
                  <div className="finding-copy">
                    <strong>{threat.threatName}</strong>
                    <span title={threat.filePath}>{threat.filePath}</span>
                    {threat.details[0] && <small>{threat.details[0]}</small>}
                  </div>
                  {threat.quarantined ? (
                    <span className="finding-isolated">In quarantine</span>
                  ) : (
                    <button
                      className="button button-secondary"
                      type="button"
                      onClick={() => void quarantineThreat(threat)}
                    >
                      Quarantine
                    </button>
                  )}
                </div>
              ))}
            </div>
          </motion.section>
        )}
      </AnimatePresence>
    </section>
  );
};
