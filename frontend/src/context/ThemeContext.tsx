import React, { createContext, useContext, useEffect, useState } from 'react';
import { ThemeConfig, ThemeContextType, ThemeMode } from '../types/theme';

export const THEMES: ThemeConfig[] = [
  {
    id: 'dark',
    name: 'Zinc',
    description: 'A quiet, balanced dark surface.',
    previewBg: '#11110f',
    previewCard: '#191916',
    previewBorder: 'rgba(255, 255, 255, 0.1)',
    previewAccent: '#ffffff',
  },
  {
    id: 'oled',
    name: 'Ink',
    description: 'Near-black surfaces for OLED displays.',
    previewBg: '#000000',
    previewCard: '#0a0a0c',
    previewBorder: 'rgba(255, 255, 255, 0.08)',
    previewAccent: '#ffffff',
  },
  {
    id: 'slate',
    name: 'Slate',
    description: 'A cool, low-contrast graphite.',
    previewBg: '#11151a',
    previewCard: '#191e24',
    previewBorder: 'rgba(255, 255, 255, 0.1)',
    previewAccent: '#38bdf8',
  },
  {
    id: 'light',
    name: 'Paper',
    description: 'Warm off-white for bright rooms.',
    previewBg: '#f4f2ec',
    previewCard: '#fffefa',
    previewBorder: 'rgba(0, 0, 0, 0.08)',
    previewAccent: '#18181b',
  },
];

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem('aegis_theme_mode') as ThemeMode;
    return saved && THEMES.some(t => t.id === saved) ? saved : 'dark';
  });

  const setTheme = (newTheme: ThemeMode) => {
    setThemeState(newTheme);
    localStorage.setItem('aegis_theme_mode', newTheme);
  };

  useEffect(() => {
    const root = document.documentElement;
    THEMES.forEach(t => root.classList.remove(`theme-${t.id}`));
    root.classList.remove('dark', 'light');

    root.setAttribute('data-theme', theme);
    root.classList.add(`theme-${theme}`);
    if (theme === 'light') {
      root.classList.add('light');
    } else {
      root.classList.add('dark');
    }
  }, [theme]);

  return (
    <ThemeContext.Provider value={{ theme, setTheme, availableThemes: THEMES }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = (): ThemeContextType => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};
