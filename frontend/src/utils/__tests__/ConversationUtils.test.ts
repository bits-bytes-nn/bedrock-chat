import { describe, expect, test } from 'vitest';
import { getCurrentConversation } from '../ConversationUtils';

const previous = { id: 'previous', shouldContinue: true };

describe('getCurrentConversation', () => {
  test('returns the data of the shown conversation', () => {
    expect(getCurrentConversation(previous, 'previous')).toBe(previous);
  });

  test('ignores the previous conversation that SWR keeps for a new chat', () => {
    expect(getCurrentConversation(previous, '')).toBeUndefined();
  });

  test('ignores the previous conversation while the next one loads', () => {
    expect(getCurrentConversation(previous, 'next')).toBeUndefined();
  });

  test('returns undefined without data', () => {
    expect(getCurrentConversation(undefined, 'next')).toBeUndefined();
  });

  test('a new chat cannot continue the previous conversation', () => {
    expect(getCurrentConversation(previous, '')?.shouldContinue ?? false).toBe(
      false
    );
  });
});
