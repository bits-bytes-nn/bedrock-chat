import { describe, expect, test } from 'vitest';
import en from '../en';
import de from '../de';
import es from '../es';
import fr from '../fr';
import id from '../id';
import it from '../it';
import ja from '../ja';
import ko from '../ko';
import ms from '../ms';
import nb from '../nb';
import pl from '../pl';
import ptbr from '../pt-br';
import th from '../th';
import vi from '../vi';
import zhhans from '../zh-hans';
import zhhant from '../zh-hant';

/** Return the dotted paths of the leaves; arrays are leaves. */
const flattenKeys = (value: unknown, prefix = ''): string[] => {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    return [prefix];
  }
  return Object.entries(value).flatMap(([key, child]) =>
    flattenKeys(child, prefix ? `${prefix}.${key}` : key)
  );
};

describe('flattenKeys', () => {
  test('flattens nested objects', () => {
    expect(flattenKeys({ a: { b: 'x', c: { d: 'y' } }, e: ['z'] })).toEqual([
      'a.b',
      'a.c.d',
      'e',
    ]);
  });
});

describe('locales', () => {
  const enKeys = new Set(flattenKeys(en));

  // English is the fallback, so a key that it does not have is never used.
  test.each(
    Object.entries({
      de,
      es,
      fr,
      id,
      it,
      ja,
      ko,
      ms,
      nb,
      pl,
      ptbr,
      th,
      vi,
      zhhans,
      zhhant,
    })
  )('%s has only keys that English has', (_, locale) => {
    expect(flattenKeys(locale).filter((key) => !enKeys.has(key))).toEqual([]);
  });
});

/** The leaves with their text, keyed by dotted path. */
const flattenTexts = (value: unknown, prefix = ''): [string, string][] => {
  if (typeof value === 'string') {
    return [[prefix, value]];
  }
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    return [];
  }
  return Object.entries(value).flatMap(([key, child]) =>
    flattenTexts(child, prefix ? `${prefix}.${key}` : key)
  );
};

/** The markup that the code fills in: components such as <Link> and variables. */
const placeholders = (text: string): string[] =>
  [...text.matchAll(/<\/?\w+>|\{\{\s*\w+\s*\}\}/g)]
    .map((match) => match[0].replace(/\s/g, ''))
    .sort();

// Translations that leave out the English reason on purpose: the reason is an
// English text from the model API (hooks/usePostMessageStreaming.ts).
const OMITTED_PLACEHOLDERS = new Set([
  'translation.error.predict.model_error',
  'translation.error.predict.invalid_request',
]);

describe('placeholders', () => {
  const english = new Map(flattenTexts(en));

  // The maintained translations must keep the links and variables.
  test.each(Object.entries({ ja, ko }))(
    '%s keeps the placeholders of English',
    (_, locale) => {
      const different = flattenTexts(locale)
        .filter(([key]) => english.has(key) && !OMITTED_PLACEHOLDERS.has(key))
        .filter(
          ([key, text]) =>
            placeholders(text).join() !== placeholders(english.get(key)!).join()
        )
        .map(([key]) => key);
      expect(different).toEqual([]);
    }
  );
});

