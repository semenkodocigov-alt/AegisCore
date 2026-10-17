import React, { useEffect } from 'react';
import { motion } from 'framer-motion';

interface SplashScreenProps {
  onComplete: () => void;
  minDurationMs?: number;
}

export const SplashScreen: React.FC<SplashScreenProps> = ({ onComplete, minDurationMs = 1250 }) => {
  useEffect(() => {
    const timer = window.setTimeout(onComplete, minDurationMs);
    return () => window.clearTimeout(timer);
  }, [minDurationMs, onComplete]);

  return (
    <motion.div
      className="splash-screen"
      initial={{ opacity: 1 }}
      exit={{ opacity: 0, transition: { duration: 0.24 } }}
    >
      <div className="splash-lockup">
        <span className="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M12 2.5 4 6v5.3c0 5 3.4 9.4 8 10.7 4.6-1.3 8-5.7 8-10.7V6l-8-3.5Z" />
            <path d="m8.8 12.3 2.1 2.1 4.5-4.7" />
          </svg>
        </span>
        <strong>Aegis <span>Core</span></strong>
        <p>Preparing your workspace</p>
      </div>
      <div className="splash-progress"><span /></div>
    </motion.div>
  );
};
