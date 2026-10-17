/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['class', '[data-theme="dark"]'],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Deep matte surfaces (Linear/Raycast aesthetic)
        canvas: {
          dark: '#09090b',       // Deep matte zinc
          oled: '#000000',       // True obsidian black
          slate: '#0b0f17',      // Technical graphite
          light: '#fbfbfa',      // Warm architectural off-white
        },
        surface: {
          dark: '#121215',       // Primary card surface
          darkElevated: '#18181b', // Elevated modal/popover surface
          oled: '#0a0a0c',
          slate: '#111726',
          light: '#ffffff',
          lightElevated: '#f4f4f5',
        },
        line: {
          dark: 'rgba(255, 255, 255, 0.08)',     // Crisp 1px subtle divider
          darkStrong: 'rgba(255, 255, 255, 0.14)',
          light: 'rgba(0, 0, 0, 0.08)',
          lightStrong: 'rgba(0, 0, 0, 0.16)',
        },
        accent: {
          primary: '#ffffff',     // Tactile white primary button on dark
          primaryDark: '#09090b', // Tactile black primary button on light
          emerald: '#10b981',     // Restrained functional green for security/health
          rose: '#f43f5e',        // Restrained alert red for malicious threats
          amber: '#f59e0b',       // Restrained warning amber
        },
      },
      borderRadius: {
        'sm': '4px',
        'DEFAULT': '6px',
        'md': '8px',
        'lg': '10px',
        'xl': '12px',
      },
      letterSpacing: {
        'tightest': '-0.035em',
        'tighter': '-0.025em',
        'tight': '-0.015em',
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'SF Mono', 'Menlo', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'subtle': '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        'elevated': '0 4px 20px -2px rgba(0, 0, 0, 0.35)',
        'modal': '0 20px 40px -15px rgba(0, 0, 0, 0.65)',
        'tactile-dark': 'inset 0 1px 0 0 rgba(255, 255, 255, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.4)',
        'tactile-light': 'inset 0 1px 0 0 rgba(255, 255, 255, 0.6), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
      },
    },
  },
  plugins: [],
};
