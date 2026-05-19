import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const LocaleContext = createContext(null);

const STORAGE_KEY = 'ui_locale';

export function LocaleProvider({ children }) {
  const [locale, setLocale] = useState(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'ar' || saved === 'en') {
      return saved;
    }
    return 'ar';
  });

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, locale);
    document.documentElement.setAttribute('lang', locale);
    document.documentElement.setAttribute('dir', locale === 'ar' ? 'rtl' : 'ltr');
    document.body.classList.toggle('lang-ar', locale === 'ar');
    document.body.classList.toggle('lang-en', locale === 'en');
  }, [locale]);

  const value = useMemo(() => ({
    locale,
    isArabic: locale === 'ar',
    setLocale,
    toggleLocale: () => setLocale((prev) => (prev === 'ar' ? 'en' : 'ar')),
  }), [locale]);

  return (
    <LocaleContext.Provider value={value}>
      {children}
    </LocaleContext.Provider>
  );
}

export function useLocale() {
  const context = useContext(LocaleContext);
  if (!context) {
    throw new Error('useLocale must be used within LocaleProvider');
  }
  return context;
}

