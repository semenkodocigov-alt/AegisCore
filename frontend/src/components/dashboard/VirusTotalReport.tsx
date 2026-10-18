import React from 'react';
import { VirusTotalResult as VirusTotalResultData } from '../../types/scanner';
import { useLanguage } from '../../context/LanguageContext';

interface VirusTotalReportProps {
  result: VirusTotalResultData;
}

export const VirusTotalReport: React.FC<VirusTotalReportProps> = ({ result }) => {
  const { t } = useLanguage();
  const detected = result.status === 'detected';
  const label = {
    clean: t('No detections'),
    detected: t('Threats detected'),
    not_found: t('No existing report'),
    queued: t('Upload complete; analysis queued'),
    rate_limited: t('Rate limit reached'),
    error: t(result.message),
  }[result.status];

  return (
    <div className="virustotal-result">
      {(result.total > 0 || detected) && (
        <span className={`virustotal-detection ${detected ? 'virustotal-detection-alert' : ''}`}>
          {t('VirusTotal')}: {result.malicious} / {result.total}
        </span>
      )}
      <span className="virustotal-result-label">{label}</span>
      {result.reportUrl && (
        <a className="virustotal-report-link" href={result.reportUrl} target="_blank" rel="noreferrer">
          {t('Open VirusTotal report')}
        </a>
      )}
      {result.detections.length > 0 && (
        <span className="virustotal-engine-list">
          {t('Detected by')}: {result.detections.map(({ engine, label: engineLabel }) => `${engine} (${engineLabel})`).join(', ')}
        </span>
      )}
    </div>
  );
};
