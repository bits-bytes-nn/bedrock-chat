type KeyInput = Pick<KeyboardEvent, 'key' | 'shiftKey' | 'isComposing' | 'keyCode'>;

/**
 * Whether the key event should submit the input: Enter without Shift, outside of IME
 * composition. The Enter that confirms Korean or Japanese input must not submit.
 */
export const isSubmitEnter = (e: KeyInput): boolean =>
  e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.keyCode !== 229;
