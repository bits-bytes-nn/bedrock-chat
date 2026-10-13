import { describe, expect, test } from 'vitest';
import { useSnackbarState } from '../useSnackbar';

describe('useSnackbarState', () => {
  test('counts every open, so that the close timer restarts', () => {
    const { open, close } = useSnackbarState.getState();
    const before = useSnackbarState.getState().openCount;

    open('first');
    open('second');

    const state = useSnackbarState.getState();
    expect(state.isOpen).toBe(true);
    expect(state.message).toBe('second');
    expect(state.openCount).toBe(before + 2);

    close();
    expect(useSnackbarState.getState().isOpen).toBe(false);
  });
});
