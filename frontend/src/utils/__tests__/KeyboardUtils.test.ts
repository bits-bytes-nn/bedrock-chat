import { describe, expect, test } from 'vitest';
import { isSubmitEnter } from '../KeyboardUtils';

const key = (overrides: Partial<Parameters<typeof isSubmitEnter>[0]>) => ({
  key: 'Enter',
  shiftKey: false,
  isComposing: false,
  keyCode: 13,
  ...overrides,
});

describe('isSubmitEnter', () => {
  test('submits on Enter', () => {
    expect(isSubmitEnter(key({}))).toBe(true);
  });

  test('keeps Shift+Enter for a new line', () => {
    expect(isSubmitEnter(key({ shiftKey: true }))).toBe(false);
  });

  test('ignores Enter while an IME is composing', () => {
    expect(isSubmitEnter(key({ isComposing: true }))).toBe(false);
    expect(isSubmitEnter(key({ keyCode: 229 }))).toBe(false);
  });
});
