import { describe, expect, test } from 'vitest';
import {
  canContinueAnswer,
  getCurrentConversation,
  joinContinuationText,
} from '../ConversationUtils';

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
});

describe('canContinueAnswer', () => {
  const cutOff = { shouldContinue: true, lastMessageId: 'answer' };

  test('continues the stored answer that was cut off', () => {
    expect(canContinueAnswer(cutOff, 'answer')).toBe(true);
  });

  test('does not continue a finished answer', () => {
    expect(
      canContinueAnswer({ ...cutOff, shouldContinue: false }, 'answer')
    ).toBe(false);
  });

  test('does not continue another branch', () => {
    expect(canContinueAnswer(cutOff, 'sibling')).toBe(false);
  });

  test('does not continue a posted answer before the refetch', () => {
    expect(canContinueAnswer(cutOff, 'new-message-assistant')).toBe(false);
  });

  test('does not continue without a loaded conversation', () => {
    expect(canContinueAnswer(undefined, 'answer')).toBe(false);
  });
});

describe('joinContinuationText', () => {
  test('shows the answer until the continuation starts', () => {
    expect(joinContinuationText('ranging up to 800°', '')).toBe(
      'ranging up to 800°'
    );
  });

  test('replaces the cut word with the rewritten one', () => {
    expect(joinContinuationText('ranging up to 800°', '800°F')).toBe(
      'ranging up to 800°F'
    );
  });

  test('keeps one space between words', () => {
    expect(joinContinuationText('due to ', ' similar')).toBe('due to similar');
    expect(joinContinuationText('due to', 'to similar')).toBe('due to similar');
  });

  test('keeps indentation after a line break', () => {
    expect(joinContinuationText('def f():\n', '    return 1')).toBe(
      'def f():\n    return 1'
    );
  });

  test('leaves Japanese text, which has no spaces between words', () => {
    expect(joinContinuationText('外に出て', 'みましょう')).toBe(
      '外に出てみましょう'
    );
  });
});
