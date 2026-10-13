import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';

vi.mock('aws-amplify/auth', () => ({
  fetchAuthSession: async () => ({ tokens: { idToken: 'header.pay+load/sig=' } }),
}));

import i18next from 'i18next';
import usePostMessageStreaming, {
  getPredictErrorMessage,
} from '../usePostMessageStreaming';
import { PostMessageRequest } from '../../@types/conversation';

class FakeWebSocket {
  static last: FakeWebSocket;
  sent: { step: string; index?: number; part?: string }[] = [];
  onopen?: () => void;
  onmessage?: (message: { data: string }) => void;
  onerror?: (e: unknown) => void;
  onclose?: (e: { code: number; reason: string }) => void;

  constructor(public url: string) {
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

const initI18n = () =>
  i18next.init({
    lng: 'en',
    resources: {
      en: {
        translation: {
          error: {
            predict: {
              general: 'general',
              connectionClosed: 'closed',
              invalidResponse: 'invalid',
              throttled: 'throttled',
              model_error: 'model error: {{reason}}',
            },
          },
        },
      },
      ko: {
        translation: {
          error: { predict: { general: 'general (ko)' } },
        },
      },
    },
  });

describe('usePostMessageStreaming', () => {
  beforeEach(async () => {
    await initI18n();
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
    expect(ws.url).toContain(
      `token=${encodeURIComponent('header.pay+load/sig=')}`
    );
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

  test('shows a localized message for a known error code', async () => {
    const { promise, ws } = await startPost();
    ws.receive({ status: 'ERROR', reason: 'Rate exceeded', code: 'throttled' });

    await expect(promise).rejects.toBe('throttled');
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

  test.each([
    '{"message": "Endpoint request timed out", "connectionId": "x"}',
    '{"connectionId":"x","message":"Endpoint request timed out"}',
  ])('ignores the API Gateway timeout frame %s', async (frame) => {
    const { promise, ws } = await startPost();
    ws.receive(frame);
    ws.receive({ status: 'STREAMING_END', stop_reason: 'end_turn' });

    await expect(promise).resolves.toBeUndefined();
  });

  test('fails on other API Gateway frames', async () => {
    const { promise, ws } = await startPost();
    ws.receive({ message: 'Internal server error', connectionId: 'x' });

    await expect(promise).rejects.toBe('general');
  });
});

describe('getPredictErrorMessage', () => {
  beforeEach(initI18n);

  test('includes the reason for model errors', () => {
    expect(
      getPredictErrorMessage({ code: 'model_error', reason: 'Bad input' })
    ).toBe('model error: Bad input');
  });

  test('falls back to the reason for unknown or missing codes', () => {
    expect(getPredictErrorMessage({ code: 'other', reason: 'No access' })).toBe(
      'No access'
    );
    expect(getPredictErrorMessage({ reason: 'No access' })).toBe('No access');
    expect(getPredictErrorMessage({})).toBe('invalid');
  });

  test('hides reasons without a known code in other languages', async () => {
    await i18next.changeLanguage('ko');
    expect(getPredictErrorMessage({ code: 'other', reason: 'No access' })).toBe(
      'general (ko)'
    );
    expect(getPredictErrorMessage({ reason: 'No access' })).toBe(
      'general (ko)'
    );
  });
});
