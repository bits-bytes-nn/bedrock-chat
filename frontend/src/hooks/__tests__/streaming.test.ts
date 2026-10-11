import { describe, expect, test } from 'vitest';
import { createActor } from 'xstate';
import { chunkPayload } from '../usePostMessageStreaming';
import { streamingStateMachine } from '../xstates/streaming';

describe('chunkPayload', () => {
  test('splits payload into chunks of the given size', () => {
    expect(chunkPayload('abcdefg', 3)).toEqual(['abc', 'def', 'g']);
  });

  test('keeps surrogate pairs in the same chunk', () => {
    const payload = 'ab😀cd';
    const chunks = chunkPayload(payload, 3);

    expect(chunks).toEqual(['ab', '😀c', 'd']);
    expect(chunks.join('')).toBe(payload);
  });

  test('returns no chunks for an empty payload', () => {
    expect(chunkPayload('', 3)).toEqual([]);
  });
});

describe('streamingStateMachine', () => {
  test('starts a fresh stream when the previous one did not end', () => {
    const actor = createActor(streamingStateMachine).start();
    actor.send({ type: 'wakeup' });
    actor.send({ type: 'text', text: 'partial answer' });

    actor.send({ type: 'wakeup' });
    actor.send({ type: 'text', text: 'new answer' });

    expect(actor.getSnapshot().value).toBe('streaming');
    expect(actor.getSnapshot().context.text).toBe('new answer');
  });

  test('accepts a new stream while leaving the previous one', () => {
    const actor = createActor(streamingStateMachine).start();
    actor.send({ type: 'wakeup' });
    actor.send({ type: 'text', text: 'first' });
    actor.send({ type: 'goodbye' });

    actor.send({ type: 'wakeup' });
    actor.send({ type: 'text', text: 'second' });

    expect(actor.getSnapshot().context.text).toBe('second');
  });
});
