import React from 'react';
import { Language, useLanguage } from '../../context/LanguageContext';

export const LanguageSwitcher: React.FC = () => {
  const { language, setLanguage, t } = useLanguage();

  return (
    <section className="account-card language-card">
      <div className="card-heading">
        <div>
          <p className="eyebrow">{t('APPLICATION')}</p>
          <h2>{t('Language')}</h2>
        </div>
      </div>
      <p className="account-copy">{t('Choose the language used throughout Aegis Core.')}</p>
      <div className="language-options" role="group" aria-label={t('Language')}>
        {(['ru', 'en'] as const).map((option: Language) => (
          <button
            key={option}
            type="button"
            className={`button ${language === option ? 'button-primary' : 'button-secondary'}`}
            aria-pressed={language === option}
            onClick={() => setLanguage(option)}
          >
            {t(option === 'ru' ? 'Russian' : 'English')}
          </button>
        ))}
      </div>
    </section>
  );
};
