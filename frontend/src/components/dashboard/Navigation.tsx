import React from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '../../context/AuthContext';
import { useLanguage } from '../../context/LanguageContext';

export type ActiveTab = 'scanner' | 'quarantine' | 'settings' | 'account';

interface NavigationProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  quarantineCount?: number;
}

const icons: Record<ActiveTab, React.ReactNode> = {
  scanner: (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M10 2.25 3.5 5v4.3c0 4.2 2.8 7.8 6.5 8.9 3.7-1.1 6.5-4.7 6.5-8.9V5L10 2.25Z" />
      <path d="m7.3 9.9 1.8 1.8 3.7-3.9" />
    </svg>
  ),
  quarantine: (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M3 6.25h14v10H3zM2.5 3.75h15M7.25 3.75l.8 2.5m4.7-2.5-.8 2.5" />
    </svg>
  ),
  settings: (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M3 5h14M3 10h14M3 15h14M7 3.5v3M12 8.5v3M8 13.5v3" />
    </svg>
  ),
  account: (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <circle cx="10" cy="6.5" r="3" />
      <path d="M4 17c.4-3 2.7-4.75 6-4.75s5.6 1.75 6 4.75" />
    </svg>
  ),
};

export const Navigation: React.FC<NavigationProps> = ({
  activeTab,
  onTabChange,
  quarantineCount = 0,
}) => {
  const { user, isGuest } = useAuth();
  const { t } = useLanguage();
  const navItems: { id: ActiveTab; label: string; badge?: number }[] = [
    { id: 'scanner', label: t('Overview') },
    { id: 'quarantine', label: t('Quarantine'), badge: quarantineCount },
    { id: 'settings', label: t('Settings') },
    { id: 'account', label: t('My account') },
  ];

  return (
    <nav className="app-navigation" aria-label={t('Main navigation')}>
      <div className="nav-items">
        {navItems.map((item) => {
          const selected = activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item ${selected ? 'nav-item-selected' : ''}`}
              type="button"
              onClick={() => onTabChange(item.id)}
              aria-current={selected ? 'page' : undefined}
            >
              <span className="nav-icon">{icons[item.id]}</span>
              <span>{item.label}</span>
              {item.badge ? <span className="nav-badge">{item.badge}</span> : null}
              {selected && (
                <motion.span
                  className="nav-indicator"
                  layoutId="active-nav-indicator"
                  transition={{ type: 'spring', stiffness: 420, damping: 34 }}
                />
              )}
            </button>
          );
        })}
      </div>
      {user && (
        <div className="nav-session">
          <span className={`session-dot ${isGuest ? 'session-dot-guest' : ''}`} />
          <span>{user.nickname}</span>
          <span className="nav-session-divider">/</span>
          <span>{t(isGuest ? 'Guest' : 'Account')}</span>
        </div>
      )}
    </nav>
  );
};
