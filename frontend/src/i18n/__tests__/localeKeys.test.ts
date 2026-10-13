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
