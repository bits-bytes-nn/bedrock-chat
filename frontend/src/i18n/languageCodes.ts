// The app uses these keys for languages with a region or script. They are kept for
// compatibility with saved settings and the OpenSearch analyzer mapping.
const APP_TO_BCP47: Record<string, string> = {
  zhhans: 'zh-Hans',
  zhhant: 'zh-Hant',
  ptbr: 'pt-BR',
};

/** Map a language detected from the browser, such as zh-TW, to the app's key. */
export const toAppLanguage = (detected: string): string => {
  const [language, region] = detected.toLowerCase().split(/[-_]/);
  if (language === 'zh') {
    return ['tw', 'hk', 'mo', 'hant'].includes(region) ? 'zhhant' : 'zhhans';
  }
  if (language === 'pt') {
    return 'ptbr';
  }
  return detected;
};

/** Map the app's language key to a BCP 47 tag for the lang attribute. */
export const toBcp47 = (language: string): string =>
  APP_TO_BCP47[language] ?? language;
