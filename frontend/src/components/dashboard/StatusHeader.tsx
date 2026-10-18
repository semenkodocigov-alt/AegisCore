import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useLanguage } from '../../context/LanguageContext';
import { apiService } from '../../services/api';

interface StatusHeaderProps {
  quarantinedCount?: number;
}

export const StatusHeader: React.FC<StatusHeaderProps> = ({ quarantinedCount = 0 }) => {
  const { t, language } = useLanguage();
  const [isAdmin, setIsAdmin] = useState(false);
  const filePlural = new Intl.PluralRules(language).select(quarantinedCount);
  useEffect(() => {
    let active = true;
    void apiService.getPrivilegeStatus().then((response) => {
      if (active && response.success && response.data) {
        setIsAdmin(response.data.isAdmin);
      }
    });
    return () => {
      active = false;
    };
  }, []);
  return <motion.section
    className="overview-status"
    initial={{ opacity: 0, y: 5 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.2 }}
  >
    <div className="overview-intro">
      <p className="eyebrow">{t('DEVICE OVERVIEW')}</p>
      <h1>{t('Security, on your terms.')}</h1>
      <p>{t('Run a local scan when you want to check a file or a set of common folders.')}</p>
      <span className={`session-badge privilege-badge ${isAdmin ? 'privilege-badge-admin' : ''}`}>
        <span aria-hidden="true" />
        {t(isAdmin ? 'Admin / Elevated' : 'Standard privileges')}
      </span>
    </div>
    <div className="overview-facts">
      <div>
        <span className="overview-fact-mark" aria-hidden="true">01</span>
        <span><small>{t('Scanning')}</small><strong>{t('On demand')}</strong></span>
      </div>
      <div>
        <span className="overview-fact-mark" aria-hidden="true">02</span>
        <span><small>{t('Processing')}</small><strong>{t('On this device')}</strong></span>
      </div>
      <div>
        <span className="overview-fact-mark" aria-hidden="true">03</span>
        <span><small>{t('In quarantine')}</small><strong>{quarantinedCount} {filePlural === 'one' ? t('file') : filePlural === 'few' ? t('filesFew') : t('files')}</strong></span>
      </div>
    </div>
  </motion.section>;
};
