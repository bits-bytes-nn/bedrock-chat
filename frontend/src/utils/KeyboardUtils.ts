import type React from 'react';

type KeyInput = Pick<
  KeyboardEvent,
  'key' | 'shiftKey' | 'isComposing' | 'keyCode'
>;

/**
 * Whether the key event should submit the input: Enter without Shift, outside of IME
 * composition. The Enter that confirms Korean or Japanese input must not submit.
 */
export const isSubmitEnter = (e: KeyInput): boolean =>
  e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.keyCode !== 229;

/**
 * Makes an element that is not a button, such as a list row that holds other
 * buttons, usable with the keyboard: focusable, announced as a button, and
 * activated with Enter or Space. Keys pressed in the row's own inputs and
 * buttons are left to them.
 */
export const clickableProps = (onClick: () => void) => ({
  role: 'button' as const,
  tabIndex: 0,
  onClick,
  onKeyDown: (e: React.KeyboardEvent) => {
    if (e.target !== e.currentTarget) {
      return;
    }
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onClick();
    }
  },
});
