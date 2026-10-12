import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: async () => ({ tokens: { idToken: 'token' } }),
}));

import i18next from 'i18next';
import usePostMessageStreaming from '../usePostMessageStreaming';
import { PostMessageRequest } from '../../@types/conversation';

class FakeWebSocket {
  static last: FakeWebSocket;
  sent: { step: string; index?: number; part?: string }[] = [];
  onopen?: () => void;
  onmessage?: (message: { data: string }) => void;
  onerror?: (e: unknown) => void;
  onclose?: (e: { code: number; reason: string }) => void;

  constructor() {
    FakeWebSocket.last = this;
    setTimeout(() => this.onopen?.());
  }
  send(data: string) {
    this.sent.push(JSON.parse(data));
  }
  close() {
    this.onclose?.({ code: 1000, reason: '' });
  }
  receive(data: string | object) {
    this.onmessage?.({
      data: typeof data === 'string' ? data : JSON.stringify(data),
    });
  }
}

const input = {
  conversationId: 'conversation',
} as unknown as PostMessageRequest;
const flush = () => new Promise((resolve) => setTimeout(resolve));

const startPost = async () => {
  const events: { type: string }[] = [];
  const promise = usePostMessageStreaming
    .getState()
    .post({ input, handleStreamingEvent: (e) => events.push(e) });
  // Wait for the auth session, then for the socket to open.
  await flush();
  await flush();
  const ws = FakeWebSocket.last;
  ws.receive('Session started.');
  ws.receive('Message part received.');
  return { promise, ws, events };
};

describe('usePostMessageStreaming', () => {
  beforeEach(async () => {
    await i18next.init({
      lng: 'en',
      resources: {
        en: {
          translation: { error: { predict: { connectionClosed: 'closed' } } },
        },
      },
    });
    vi.stubGlobal('WebSocket', FakeWebSocket);
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test('sends START, the body and END, then resolves on STREAMING_END', async () => {
    const { promise, ws, events } = await startPost();
    ws.receive({ status: 'STREAMING', completion: 'Hi' });
    ws.receive({ status: 'STREAMING_END', stop_reason: 'max_tokens' });

    await expect(promise).resolves.toBeUndefined();
    expect(ws.sent.map((m) => m.step)).toEqual(['START', 'BODY', 'END']);
    expect(events.map((e) => e.type)).toEqual(['wakeup', 'text', 'goodbye']);
    expect(usePostMessageStreaming.getState().truncatedConversationId).toBe(
      'conversation'
    );
  });

  test('keeps the error reason when the socket closes afterwards', async () => {
    const { promise, ws } = await startPost();
    ws.receive({ status: 'ERROR', reason: 'No access' });

    await expect(promise).rejects.toBe('No access');
    const state = usePostMessageStreaming.getState();
    expect(state.errorDetail).toBe('No access');
    expect(state.errorConversationId).toBe('conversation');
  });

  test('rejects when the connection closes before the end of the stream', async () => {
    const { promise, ws } = await startPost();
    ws.receive({ status: 'STREAMING', completion: 'partial' });
    ws.close();

    await expect(promise).rejects.toBe(
      i18next.t('error.predict.connectionClosed')
    );
  });

  test('limits the message parts in flight and sends them in order', async () => {
    const largeInput = {
      conversationId: 'conversation',
      message: 'x'.repeat(8 * 1024 * 60),
    } as unknown as PostMessageRequest;
    usePostMessageStreaming
      .getState()
      .post({ input: largeInput, handleStreamingEvent: () => {} });
    await flush();
    await flush();
    const ws = FakeWebSocket.last;
    const bodies = () => ws.sent.filter((m) => m.step === 'BODY');

    ws.receive('Session started.');
    expect(bodies()).toHaveLength(50);

    while (!ws.sent.some((m) => m.step === 'END')) {
      ws.receive('Message part received.');
    }
    expect(bodies().map((m) => m.index)).toEqual(
      bodies().map((_, index) => index)
    );
    expect(bodies().map((m) => m.part).join('')).toContain('x'.repeat(1000));
    expect(bodies().every((m) => (m.part ?? '').length <= 8 * 1024)).toBe(true);
  });

  test('ignores the API Gateway timeout message', async () => {
    const { promise, ws } = await startPost();
    ws.receive(
      '{"message": "Endpoint request timed out", "connectionId": "x"}'
    );
    ws.receive({ status: 'STREAMING_END', stop_reason: 'end_turn' });

    await expect(promise).resolves.toBeUndefined();
  });
});
