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
