/**
 * Return the data only if it belongs to the conversation. SWR keeps returning the
 * previous conversation while the next one loads, and also for a new chat.
 *
 * @param data The data returned by SWR.
 * @param conversationId The ID of the shown conversation, empty for a new chat.
 */
export const getCurrentConversation = <T extends { id: string }>(
  data: T | undefined,
  conversationId: string
): T | undefined =>
  conversationId !== '' && data?.id === conversationId ? data : undefined;

/**
 * Whether the shown answer can be continued: the stored last answer stopped at
 * the output limit, and it is the one shown. Another branch, or a posted message
 * that still has its temporary id, would be joined to the wrong answer.
 *
 * @param conversation The shown conversation, if loaded.
 * @param shownLastMessageId The ID of the last shown message.
 */
export const canContinueAnswer = (
  conversation: { shouldContinue: boolean; lastMessageId: string } | undefined,
  shownLastMessageId: string | undefined
): boolean =>
  !!conversation?.shouldContinue &&
  shownLastMessageId === conversation.lastMessageId;

// Mirrors drop_partial_word and join_continuation in
// backend/app/repositories/models/conversation.py, so that the streamed
// continuation looks like the answer that will be stored.
// No lookbehind: Safari before 16.4 cannot parse it.
const PARTIAL_WORD =
  /(\s)[^\s\u3040-\u30ff\u3400-\u9fff\uf900-\ufaff\uff00-\uffef]+$/;

/**
 * The text of a cut-off answer joined with its streamed continuation. The
 * backend sends the answer without its last, possibly cut, word, which the model
 * writes again, and keeps one space between words.
 *
 * @param answer The text of the cut-off answer.
 * @param continuation The continuation streamed so far.
 */
export const joinContinuationText = (
  answer: string,
  continuation: string
): string => {
  if (!continuation.trim()) {
    return answer;
  }
  const dropped = answer.replace(PARTIAL_WORD, '$1');
  // Nothing but whitespace would be left, so the backend keeps the word.
  const head = dropped.trim() ? dropped : answer;
  return /[ \t]$/.test(head)
    ? head + continuation.replace(/^[ \t]+/, '')
    : head + continuation;
};
