import React, { useState } from 'react';

interface TitleBarProps {
  appName?: string;
}

export const TitleBar: React.FC<TitleBarProps> = ({ appName = 'Aegis Core' }) => {
  const [isMaximized, setIsMaximized] = useState(false);

  const minimize = () => window.pywebview?.api?.minimize();
  const maximize = () => {
    window.pywebview?.api?.toggle_maximize();
    setIsMaximized((value) => !value);
  };
  const close = () => window.pywebview?.api?.close();

  return (
    <header className="title-bar window-drag-region pywebview-drag-region">
      <div className="title-bar-brand">
        <span className="title-bar-mark" aria-hidden="true">A</span>
        <span>{appName}</span>
        <span className="title-bar-version">DESKTOP</span>
      </div>
      <div className="window-controls window-no-drag pywebview-no-drag">
        <button className="window-no-drag pywebview-no-drag" type="button" aria-label="Minimize window" onClick={minimize}>−</button>
        <button
          className="window-no-drag pywebview-no-drag"
          type="button"
          aria-label={isMaximized ? 'Restore window' : 'Maximize window'}
          onClick={maximize}
        >
          {isMaximized ? '▢' : '□'}
        </button>
        <button type="button" aria-label="Close window" className="window-close window-no-drag pywebview-no-drag" onClick={close}>×</button>
      </div>
    </header>
  );
};
