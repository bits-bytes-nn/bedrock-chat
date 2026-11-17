import { describe, expect, test, vi } from 'vitest';
import { clickableProps, isSubmitEnter } from '../KeyboardUtils';

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

describe('clickableProps', () => {
  const press = (key: string, onTheRow = true) => {
    const onClick = vi.fn();
    const props = clickableProps(onClick);
    const row = {};
    const preventDefault = vi.fn();
    props.onKeyDown({
      key,
      target: onTheRow ? row : {},
      currentTarget: row,
      preventDefault,
    } as unknown as React.KeyboardEvent);
    return { onClick, preventDefault };
  };

  test('is a focusable button', () => {
    const props = clickableProps(() => {});
    expect(props.role).toBe('button');
    expect(props.tabIndex).toBe(0);
  });

  test.each(['Enter', ' '])('%j activates it', (key) => {
    const { onClick, preventDefault } = press(key);
    expect(onClick).toHaveBeenCalledOnce();
    expect(preventDefault).toHaveBeenCalledOnce();
  });

  test('other keys do not', () => {
    expect(press('a').onClick).not.toHaveBeenCalled();
  });

  test('keys in an input or button inside the row are left to it', () => {
    expect(press('Enter', false).onClick).not.toHaveBeenCalled();
  });
});
