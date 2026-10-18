import React, { useState } from 'react';
import { useLanguage } from '../../context/LanguageContext';

interface TitleBarProps {
  appName?: string;
}

export const TitleBar: React.FC<TitleBarProps> = ({ appName = 'Aegis Core' }) => {
  const [isMaximized, setIsMaximized] = useState(false);
  const { t } = useLanguage();

  const minimize = () => window.pywebview?.api?.minimize();
  const maximize = () => {
    window.pywebview?.api?.toggle_maximize();
    setIsMaximized((value) => !value);
  };
  const close = () => window.pywebview?.api?.close();
  const startDrag = (event: React.MouseEvent<HTMLElement>) => {
    if (
      event.button !== 0 ||
      (event.target instanceof Element &&
        event.target.closest('button, input, select, textarea, a, [role="button"], [data-no-drag]'))
    ) {
      return;
    }

    void window.pywebview?.api?.start_native_drag();
  };

  return (
    <header
      className="title-bar window-drag-region pywebview-drag-region"
      onMouseDown={startDrag}
    >
      <div className="title-bar-brand">
        <span className="title-bar-mark" aria-hidden="true">A</span>
        <span>{appName}</span>
        <span className="title-bar-version">DESKTOP</span>
      </div>
      <div className="window-controls window-no-drag pywebview-no-drag">
        <button className="window-no-drag pywebview-no-drag" type="button" aria-label={t('Minimize window')} onClick={minimize}>−</button>
        <button
          className="window-no-drag pywebview-no-drag"
          type="button"
          aria-label={t(isMaximized ? 'Restore window' : 'Maximize window')}
          onClick={maximize}
        >
          {isMaximized ? '▢' : '□'}
        </button>
        <button type="button" aria-label={t('Close window')} className="window-close window-no-drag pywebview-no-drag" onClick={close}>×</button>
      </div>
    </header>
  );
};
