export type ThemeMode = 'dark' | 'light' | 'oled' | 'slate';

export interface ThemeConfig {
  id: ThemeMode;
  name: string;
  description: string;
  previewBg: string;
  previewCard: string;
  previewBorder: string;
  previewAccent: string;
}

export interface ThemeContextType {
  theme: ThemeMode;
  setTheme: (theme: ThemeMode) => void;
  availableThemes: ThemeConfig[];
}
