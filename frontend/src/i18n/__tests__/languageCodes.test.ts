import { describe, expect, test } from 'vitest';
import { toAppLanguage, toBcp47 } from '../languageCodes';

describe('toAppLanguage', () => {
  test.each([
    ['zh-CN', 'zhhans'],
    ['zh-Hans', 'zhhans'],
    ['zh-TW', 'zhhant'],
    ['zh-HK', 'zhhant'],
    ['pt-BR', 'ptbr'],
    ['ko-KR', 'ko'],
    ['en-US', 'en'],
    ['nb_NO', 'nb'],
    ['en', 'en'],
    // Keys that the app saved before are kept.
    ['zhhant', 'zhhant'],
    ['ptbr', 'ptbr'],
  ])('maps %s to %s', (detected, expected) => {
    expect(toAppLanguage(detected)).toBe(expected);
  });
});

describe('toBcp47', () => {
  test('maps app keys to language tags', () => {
    expect(toBcp47('zhhant')).toBe('zh-Hant');
    expect(toBcp47('ko')).toBe('ko');
  });
});
