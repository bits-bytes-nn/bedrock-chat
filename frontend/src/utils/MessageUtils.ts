import { DisplayMessageContent, MessageMap, RelatedDocument, UsedChunk } from '../@types/conversation';

// IDs of the messages that are shown before the backend saves them.
export const NEW_MESSAGE_ID = {
  USER: 'new-message',
  ASSISTANT: 'new-message-assistant',
};

/** Whether the message is shown before the backend saves it. */
export const isTemporaryMessageId = (messageId: string): boolean =>
  messageId.startsWith(NEW_MESSAGE_ID.USER);

/** Whether an edited message has text and differs from the original. */
export const canSubmitEditedContent = (
  original: string,
  edited: string
): boolean => edited.trim() !== '' && edited.trim() !== original.trim();

export const convertMessageMapToArray = (
  messageMap: MessageMap,
  currentMessageId: string
): DisplayMessageContent[] => {
  if (Object.keys(messageMap).length === 0) {
    return [];
  }

  const messageArray: DisplayMessageContent[] = [];
  let key: string | null = currentMessageId;
  let messageContent: MessageMap[string] = messageMap[key];

  // The given key exists.
  if (messageContent) {
    // Find the leaf key.
    while (messageContent.children.length > 0) {
      key = messageContent.children[0];
      messageContent = messageMap[key];
    }

    // Add the messages from the leaf to the root.
    while (key) {
      messageContent = messageMap[key];
      // Stop when a reference is broken.
      if (!messageContent) {
        messageArray[0].parent = null;
        break;
      }

      // Stop when the message is already in the array: the references form
      // a cycle.
      if (
        messageArray.some((a) => {
          return a.id === key || a.children.includes(key ?? '');
        })
      ) {
        messageArray[0].parent = null;
        break;
      }

      messageArray.unshift({
        id: key,
        model: messageContent.model,
        role: messageContent.role,
        content: messageContent.content,
        parent: messageContent.parent,
        children: messageContent.children,
        sibling: [],
        feedback: messageContent.feedback,
        usedChunks: messageContent.usedChunks,
        thinkingLog: messageContent.thinkingLog,
      });

      key = messageContent.parent;
    }

    // The given key does not exist.
  } else {
    // Find the root key.
    key = Object.keys(messageMap).filter(
      (k) => messageMap[k].parent === null
    )[0];

    // Add the messages from the root to the leaf.
    while (key) {
      messageContent = messageMap[key];
      // Stop when a reference is broken.
      if (!messageContent) {
        messageArray[messageArray.length - 1].children = [];
        break;
      }

      // Stop when the message is already in the array: the references form
      // a cycle.
      if (
        messageArray.some((a) => {
          return a.id === key;
        })
      ) {
        messageArray[messageArray.length - 1].children = [];
        break;
      }

      messageArray.push({
        id: key,
        model: messageContent.model,
        role: messageContent.role,
        content: messageContent.content,
        parent: messageContent.parent,
        children: messageContent.children,
        sibling: [],
        feedback: messageContent.feedback,
        usedChunks: messageContent.usedChunks,
        thinkingLog: messageContent.thinkingLog,
      });
      key = messageContent.children[0];
    }
  }

  // Set the siblings.
  messageArray[0].sibling = [messageArray[0].id];
  messageArray.forEach((m, idx) => {
    if (m.children.length > 0) {
      messageArray[idx + 1].sibling = [...m.children];
    }
  });
  // Remove the system message at the top, if any.
  if (messageArray[0].id === 'system') {
    messageArray.shift();
  }

  return messageArray;
};

const isSameValue = (a: unknown, b: unknown): boolean =>
  a === b ||
  (Array.isArray(a) &&
    Array.isArray(b) &&
    a.length === b.length &&
    a.every((value, idx) => value === b[idx]));

const isSameDisplayMessage = (
  a: DisplayMessageContent,
  b: DisplayMessageContent
): boolean => {
  const keys = new Set([...Object.keys(a), ...Object.keys(b)]);
  return [...keys].every((key) =>
    isSameValue(
      a[key as keyof DisplayMessageContent],
      b[key as keyof DisplayMessageContent]
    )
  );
};

/**
 * Keep the objects of the messages that did not change, so that memoized
 * components skip them. convertMessageMapToArray builds new objects on every call,
 * for example on every frame of a streamed answer.
 *
 * @param previous The messages returned by the previous call.
 * @param next The messages that were just built.
 * @returns previous itself when no message changed.
 */
export const reuseUnchangedMessages = (
  previous: DisplayMessageContent[],
  next: DisplayMessageContent[]
): DisplayMessageContent[] => {
  const previousById = new Map(previous.map((m) => [m.id, m]));
  const messages = next.map((m) => {
    const previousMessage = previousById.get(m.id);
    return previousMessage && isSameDisplayMessage(previousMessage, m)
      ? previousMessage
      : m;
  });
  return isSameValue(previous, messages) ? previous : messages;
};

export const convertUsedChunkToRelatedDocument = (usedChunk: UsedChunk): RelatedDocument => {
  switch(usedChunk.contentType) {
    case 's3': {
      return {
        content: {
          text: usedChunk.content,
        },
        sourceId: usedChunk.rank.toString(),
        sourceName: decodeURIComponent(usedChunk.source.split('?')[0].split('/').pop() ?? ''),
        sourceLink: usedChunk.source,
      };
    }
    default: {
      return {
        content: {
          text: usedChunk.content,
        },
        sourceId: usedChunk.rank.toString(),
        sourceLink: usedChunk.source,
      };
    }
  }
};
