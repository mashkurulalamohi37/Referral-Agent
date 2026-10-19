import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import { en } from './en';
import { bn } from './bn';

export type Locale = 'en' | 'bn';
const LOCALE_KEY = 'rp.locale';

function initialLocale(): Locale {
  try {
    const saved = window.localStorage.getItem(LOCALE_KEY);
    if (saved === 'en' || saved === 'bn') return saved;
  } catch {
    /* ignore */
  }
  return navigator.language?.toLowerCase().startsWith('bn') ? 'bn' : 'en';
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, bn: { translation: bn } },
  lng: initialLocale(),
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  returnNull: false,
});

function syncDocumentLang(lng: string): void {
  document.documentElement.lang = lng;
}
syncDocumentLang(i18n.language);
i18n.on('languageChanged', syncDocumentLang);

export function setLocale(locale: Locale): void {
  try {
    window.localStorage.setItem(LOCALE_KEY, locale);
  } catch {
    /* ignore */
  }
  void i18n.changeLanguage(locale);
}

/** Locale for Intl (numbers keep Latin digits by default; Bengali digits with bn-BD). */
export function intlLocale(lng: string = i18n.language): string {
  return lng === 'bn' ? 'bn-BD' : 'en-BD';
}

export default i18n;
