import { fetchAuthSession } from 'aws-amplify/auth';
import { PostMessageRequest } from '../@types/conversation';
import { create } from 'zustand';
import i18next from 'i18next';
import { StreamingEvent } from './xstates/streaming';
import { PostStreamingStatus } from '../constants';
import { isEnglishLanguage } from '../utils/ErrorUtils';

const WS_ENDPOINT: string = import.meta.env.VITE_APP_WS_ENDPOINT;
// API Gateway closes the connection for frames over 32 KB. 8K UTF-16 code units
// stay below that in UTF-8 even for Korean or Japanese text and JSON escaping.
const CHUNK_SIZE = 8 * 1024;
// Each part runs a Lambda invocation, so limit the parts in flight.
const MAX_PARTS_IN_FLIGHT = 50;

const isHighSurrogate = (charCode: number) =>
  charCode >= 0xd800 && charCode <= 0xdbff;

/** Split the payload without breaking a surrogate pair across chunks. */
export const chunkPayload = (payload: string, chunkSize: number): string[] => {
  const chunks: string[] = [];
  let start = 0;
  while (start < payload.length) {
    let end = Math.min(start + chunkSize, payload.length);
    if (
      end < payload.length &&
      end - start > 1 &&
      isHighSurrogate(payload.charCodeAt(end - 1))
    ) {
      end--;
    }
    chunks.push(payload.substring(start, end));
    start = end;
  }
  return chunks;
};

// Error codes of ERROR frames that have a localized message.
const PREDICT_ERROR_CODES = [
  'throttled',
  'model_unavailable',
  'model_error',
  'bot_not_found',
  'invalid_request',
  'generation_failed',
  'input_too_long',
  'message_too_large',
  'conversation_too_large',
  'unauthorized',
] as const;
type PredictErrorCode = (typeof PREDICT_ERROR_CODES)[number];
const isPredictErrorCode = (code: unknown): code is PredictErrorCode =>
  PREDICT_ERROR_CODES.includes(code as PredictErrorCode);

/**
 * Return the message to show for an ERROR frame.
 *
 * The reason is the backend's English message. Only the English texts of
 * `model_error` and `invalid_request` include it, and a reason without a known
 * code is shown only in English; other languages get the generic message.
 */
export const getPredictErrorMessage = ({
  code,
  reason,
}: {
  code?: unknown;
  reason?: string;
}): string => {
  if (isPredictErrorCode(code)) {
    return i18next.t(`error.predict.${code}`, { reason });
  }
  if (!reason) {
    return i18next.t('error.predict.invalidResponse');
  }
  return isEnglishLanguage() ? reason : i18next.t('error.predict.general');
};

const usePostMessageStreaming = create<{
  post: (params: {
    input: PostMessageRequest;
    handleStreamingEvent: (event: StreamingEvent) => void;
  }) => Promise<void>;
  errorDetail: string | null;
  /** Conversation that the error belongs to. */
  errorConversationId: string | null;
  /** Conversation whose last answer stopped at the maximum output tokens. */
  truncatedConversationId: string | null;
}>((set) => {
  return {
    errorDetail: null,
    errorConversationId: null,
    truncatedConversationId: null,
    post: async ({ input, handleStreamingEvent }) => {
      set({
        errorDetail: null,
        errorConversationId: null,
        truncatedConversationId: null,
      });
      handleStreamingEvent({ type: 'wakeup' });

      const token = (await fetchAuthSession()).tokens?.idToken?.toString();
      const payloadString = JSON.stringify({
        ...input,
        token,
      });

      const chunkedPayloads = chunkPayload(payloadString, CHUNK_SIZE);

      let receivedCount = 0;
      let sentCount = 0;
      let streamEnded = false;
      let failed = false;
      return new Promise<void>((resolve, reject) => {
        // The $connect authorizer reads the token; browsers cannot set headers here.
        const ws = new WebSocket(
          `${WS_ENDPOINT}?token=${encodeURIComponent(token ?? '')}`
        );

        const fail = (reason: string) => {
          // Closing the socket below triggers onclose, so report only the first failure.
          if (failed) {
            return;
          }
          failed = true;
          set({ errorDetail: reason, errorConversationId: input.conversationId });
          ws.close();
          reject(reason);
        };

        const sendParts = () => {
          while (
            sentCount < chunkedPayloads.length &&
            sentCount - receivedCount < MAX_PARTS_IN_FLIGHT
          ) {
            ws.send(
              JSON.stringify({
                step: PostStreamingStatus.BODY,
                index: sentCount,
                part: chunkedPayloads[sentCount],
              })
            );
            sentCount++;
          }
        };

        ws.onopen = () => {
          ws.send(
            JSON.stringify({
              step: PostStreamingStatus.START,
              token: token,
            })
          );
        };

        ws.onmessage = (message) => {
          try {
            if (message.data === '' || message.data === 'Message sent.') {
              return;
            } else if (message.data === 'Session started.') {
              sendParts();
              return;
            } else if (message.data === 'Message part received.') {
              receivedCount++;
              sendParts();
              if (receivedCount === chunkedPayloads.length) {
                ws.send(
                  JSON.stringify({
                    step: PostStreamingStatus.END,
                    token: token,
                  })
                );
              }
              return;
            }

            const data = JSON.parse(message.data);

            if (data.status) {
              switch (data.status) {
                case PostStreamingStatus.AGENT_THINKING: {
                  Object.entries(data.log).forEach(([toolUseId, toolInfo]) => {
                    const typedToolInfo = toolInfo as {
                      name: string;
                      input: { [key: string]: any }; // eslint-disable-line @typescript-eslint/no-explicit-any
                    };
                    handleStreamingEvent({
                      type: 'tool-use',
                      toolUseId: toolUseId,
                      name: typedToolInfo.name,
                      input: typedToolInfo.input,
                    });
                  });
                  break;
                }
                case PostStreamingStatus.AGENT_TOOL_RESULT:
                  handleStreamingEvent({
                    type: 'tool-result',
                    toolUseId: data.result.toolUseId,
                    status: data.result.status,
                  });
                  break;
                case PostStreamingStatus.AGENT_RELATED_DOCUMENT:
                  handleStreamingEvent({
                    type: 'related-document',
                    toolUseId: data.result.toolUseId,
                    relatedDocument: data.result.relatedDocument,
                  });
                  break;
                case PostStreamingStatus.REASONING:
                  handleStreamingEvent({
                    type: 'reasoning',
                    reasoning: data.completion,
                  });
                  break;
                case PostStreamingStatus.STREAMING:
                  handleStreamingEvent({
                    type: 'text',
                    text: data.completion,
                  });
                  break;
                case PostStreamingStatus.STREAMING_END:
                  streamEnded = true;
                  if (data.stop_reason === 'max_tokens') {
                    set({ truncatedConversationId: input.conversationId });
                  }
                  handleStreamingEvent({
                    type: 'goodbye',
                  });
                  ws.close();
                  break;
                case PostStreamingStatus.ERROR:
                  console.error(data);
                  fail(getPredictErrorMessage(data));
                  break;
                default:
                  console.warn('[FRONTEND_WS] Ignored status:', data.status);
                  break;
              }
            } else if (typeof data.message === 'string') {
              // API Gateway frames carry a message but no status.
              if (data.message === 'Endpoint request timed out') {
                // The integration timed out, but the handler keeps streaming.
                return;
              }
              console.error('[FRONTEND_WS] API Gateway error:', data);
              fail(i18next.t('error.predict.general'));
            } else {
              console.error(data);
              fail(i18next.t('error.predict.invalidResponse'));
            }
          } catch (e) {
            console.error('[FRONTEND_WS] Failed to handle message:', e);
            fail(i18next.t('error.predict.general'));
          }
        };

        ws.onerror = (e) => {
          console.error('[FRONTEND_WS] WebSocket error:', e);
          fail(i18next.t('error.predict.general'));
        };
        ws.onclose = (event) => {
          if (streamEnded) {
            resolve();
            return;
          }
          // The connection was closed before STREAMING_END, so the displayed answer is incomplete.
          console.error(
            '[FRONTEND_WS] Closed before the end of the stream:',
            event.code
          );
          fail(i18next.t('error.predict.connectionClosed'));
        };
      });
    },
  };
});

export default usePostMessageStreaming;
