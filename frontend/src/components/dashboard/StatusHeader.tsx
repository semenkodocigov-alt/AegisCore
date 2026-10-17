import React from 'react';
import { motion } from 'framer-motion';

interface StatusHeaderProps {
  quarantinedCount?: number;
}

export const StatusHeader: React.FC<StatusHeaderProps> = ({ quarantinedCount = 0 }) => (
  <motion.section
    className="overview-status"
    initial={{ opacity: 0, y: 5 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.2 }}
  >
    <div className="overview-intro">
      <p className="eyebrow">DEVICE OVERVIEW</p>
      <h1>Security, on your terms.</h1>
      <p>Run a local scan when you want to check a file or a set of common folders.</p>
    </div>
    <div className="overview-facts">
      <div>
        <span className="overview-fact-mark" aria-hidden="true">01</span>
        <span><small>Scanning</small><strong>On demand</strong></span>
      </div>
      <div>
        <span className="overview-fact-mark" aria-hidden="true">02</span>
        <span><small>Processing</small><strong>On this device</strong></span>
      </div>
      <div>
        <span className="overview-fact-mark" aria-hidden="true">03</span>
        <span><small>In quarantine</small><strong>{quarantinedCount} {quarantinedCount === 1 ? 'file' : 'files'}</strong></span>
      </div>
    </div>
  </motion.section>
);
