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
