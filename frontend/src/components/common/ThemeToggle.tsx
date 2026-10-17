import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useTheme } from '../../context/ThemeContext';

export const ThemeToggle: React.FC = () => {
  const { theme, setTheme, availableThemes } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const currentTheme = availableThemes.find((t) => t.id === theme) || availableThemes[0];

  return (
    <div className="relative inline-block text-left">
      <motion.button
        whileTap={{ scale: 0.97 }}
        onClick={() => setIsOpen((open) => !open)}
        className="button button-secondary"
        aria-expanded={isOpen}
      >
        Theme: {currentTheme.name}
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.95 }}
            transition={{ duration: 0.15, ease: 'easeOut' }}
            className="theme-menu"
          >
            {availableThemes.map((t) => {
              const isActive = t.id === theme;
              return (
                <button
                  key={t.id}
                  onClick={() => {
                    setTheme(t.id);
                    setIsOpen(false);
                  }}
                  className={`theme-menu-item ${isActive ? 'theme-menu-item-selected' : ''}`}
                >
                  <span>{t.name}</span>
                  {isActive && <span aria-label="Selected">✓</span>}
                </button>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
