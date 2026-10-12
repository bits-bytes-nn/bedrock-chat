import { fetchAuthSession } from 'aws-amplify/auth';
import { PostMessageRequest } from '../@types/conversation';
import { create } from 'zustand';
import i18next from 'i18next';
import { StreamingEvent } from './xstates/streaming';
import { PostStreamingStatus } from '../constants';

const WS_ENDPOINT: string = import.meta.env.VITE_APP_WS_ENDPOINT;
const CHUNK_SIZE = 32 * 1024; //32KB

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
      let streamEnded = false;
      let failed = false;
      return new Promise<void>((resolve, reject) => {
        const ws = new WebSocket(WS_ENDPOINT);

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
            if (
              message.data === '' ||
              message.data === 'Message sent.' ||
              // Ignore timeout message from api gateway
              message.data.startsWith(
                '{"message": "Endpoint request timed out",'
              )
            ) {
              return;
            } else if (message.data === 'Session started.') {
              chunkedPayloads.forEach((chunk, index) => {
                ws.send(
                  JSON.stringify({
                    step: PostStreamingStatus.BODY,
                    index,
                    part: chunk,
                  })
                );
              });
              return;
            } else if (message.data === 'Message part received.') {
              receivedCount++;
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
                  fail(
                    data.reason || i18next.t('error.predict.invalidResponse')
                  );
                  break;
                default:
                  console.warn('[FRONTEND_WS] Ignored status:', data.status);
                  break;
              }
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
