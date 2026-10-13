import { useCallback, useEffect, useMemo } from 'react';
import useConversationApi from './useConversationApi';
import { produce } from 'immer';
import {
  MessageContent,
  DisplayMessageContent,
  MessageMap,
  Model,
  PostMessageRequest,
  Conversation,
  PutFeedbackRequest,
  TextContent,
  Content,
  ImageContent,
  AttachmentContent,
} from '../@types/conversation';
import useConversation from './useConversation';
import { create } from 'zustand';
import usePostMessageStreaming from './usePostMessageStreaming';
import { ulid } from 'ulid';
import { convertMessageMapToArray } from '../utils/MessageUtils';
import useModel from './useModel';
import useFeedbackApi from './useFeedbackApi';
import { useActorRef, useSelector } from '@xstate/react';
import { streamingStateMachine } from './xstates/streaming';
import { Actor } from 'xstate';
import i18next from 'i18next';
import useSnackbar from './useSnackbar';

/**
 * Apply streamed text at most once per animation frame. Rendering on every token
 * re-renders the whole conversation and makes long answers slow.
 *
 * @returns A function that unsubscribes and applies any text that is still pending.
 */
const subscribeStreamingText = (
  actor: Actor<typeof streamingStateMachine>,
  onText: (text: string) => void
) => {
  let frame: number | null = null;
  let latestText = '';
  const subscription = actor.subscribe((state) => {
    latestText = state.context.text;
    if (frame === null) {
      frame = requestAnimationFrame(() => {
        frame = null;
        onText(latestText);
      });
    }
  });

  return () => {
    subscription.unsubscribe();
    if (frame !== null) {
      cancelAnimationFrame(frame);
      onText(latestText);
    }
  };
};

type ChatStateType = {
  [id: string]: MessageMap;
};

type BotInputType = {
  botId: string;
  hasKnowledge: boolean;
  hasAgent: boolean;
};

export type AttachmentType = {
  fileName: string;
  fileType: string;
  extractedContent: string;
};

const NEW_MESSAGE_ID = {
  USER: 'new-message',
  ASSISTANT: 'new-message-assistant',
};
const USE_STREAMING: boolean =
  import.meta.env.VITE_APP_USE_STREAMING === 'true';

const getTextContentBody = (content: Content[]): string => {
  const textContent = content.find(
    (c): c is TextContent => c.contentType === 'text'
  );
  return textContent?.body || '';
};

const useChatState = create<{
  conversationId: string;
  setConversationId: (s: string) => void;
  postingMessage: boolean;
  // The conversation that the message is posted to. Other conversations can
  // still load while it streams.
  postingConversationId: string | null;
  setPostingMessage: (b: boolean) => void;
  // Incremented by every new chat, so that a finished new conversation does not
  // reopen after the user has started another one.
  newChatCount: number;
  chats: ChatStateType;
  setMessages: (id: string, messageMap: MessageMap) => void;
  copyMessages: (fromId: string, toId: string) => void;
  pushMessage: (
    id: string,
    parentMessageId: string | null,
    currentMessageId: string,
    content: MessageContent
  ) => void;
  removeMessage: (id: string, messageId: string) => void;
  editMessage: (id: string, messageId: string, content: string) => void;
  getMessages: (
    id: string,
    currentMessageId: string
  ) => DisplayMessageContent[];
  currentMessageId: string;
  setCurrentMessageId: (s: string) => void;
  isGeneratedTitle: boolean;
  setIsGeneratedTitle: (b: boolean) => void;
  getPostedModel: () => Model;
  shouldUpdateMessages: (currentConversation: Conversation) => boolean;
  shouldCotinue: boolean;
  setShouldContinue: (b: boolean) => void;
  getShouldContinue: () => boolean;
  reasoningEnabled: boolean;
  setReasoningEnabled: (enabled: boolean) => void;
}>((set, get) => {
  return {
    conversationId: '',
    setConversationId: (s) => {
      set(() => {
        return {
          conversationId: s,
        };
      });
    },
    postingMessage: false,
    postingConversationId: null,
    setPostingMessage: (b) => {
      set((state) => ({
        postingMessage: b,
        postingConversationId: b ? state.conversationId : null,
      }));
    },
    newChatCount: 0,
    chats: {},
    setMessages: (id: string, messageMap: MessageMap) => {
      set((state) => ({
        chats: produce(state.chats, (draft) => {
          draft[id] = messageMap;
        }),
      }));
    },
    copyMessages: (fromId: string, toId: string) => {
      set((state) => ({
        chats: produce(state.chats, (draft) => {
          draft[toId] = JSON.parse(JSON.stringify(draft[fromId]));
        }),
      }));
    },
    pushMessage: (
      id: string,
      parentMessageId: string | null,
      currentMessageId: string,
      content: MessageContent
    ) => {
      set(() => ({
        chats: produce(get().chats, (draft) => {
          // 追加対象が子ノードの場合は親ノードに参照情報を追加
          if (draft[id] && parentMessageId && parentMessageId !== 'system') {
            draft[id][parentMessageId] = {
              ...draft[id][parentMessageId],
              children: [
                ...draft[id][parentMessageId].children,
                currentMessageId,
              ],
            };
            draft[id][currentMessageId] = {
              ...content,
              parent: parentMessageId,
              children: [],
            };
          } else {
            draft[id] = {
              [currentMessageId]: {
                ...content,
                children: [],
                parent: null,
              },
            };
          }
        }),
      }));
    },
    editMessage: (id: string, messageId: string, content: string) => {
      set(() => ({
        chats: produce(get().chats, (draft) => {
          // The conversation may have been cleared, e.g. by New chat while streaming.
          if (!draft[id]?.[messageId]) {
            return;
          }
          const textContent = draft[id][messageId].content.find(
            (c) => c.contentType === 'text'
          );
          if (textContent && textContent.body !== content) {
            textContent.body = content;
          }
        }),
      }));
    },
    removeMessage: (id: string, messageId: string) => {
      set((state) => ({
        chats: produce(state.chats, (draft) => {
          if (!draft[id]?.[messageId]) {
            return;
          }
          const childrenIds = [...draft[id][messageId].children];

          // childrenに設定されているノードも全て削除
          while (childrenIds.length > 0) {
            const targetId = childrenIds.pop()!;
            childrenIds.push(...draft[id][targetId].children);
            delete draft[id][targetId];
          }

          // 削除対象のノードを他ノードの参照から削除
          Object.keys(draft[id]).forEach((key) => {
            const idx = draft[id][key].children.findIndex(
              (c) => c === messageId
            );
            if (idx > -1) {
              draft[id][key].children.splice(idx, 1);
            }
          });
          delete draft[id][messageId];
        }),
      }));
    },
    getMessages: (id: string, currentMessageId: string) => {
      return convertMessageMapToArray(get().chats[id] ?? {}, currentMessageId);
    },
    currentMessageId: '',
    setCurrentMessageId: (s: string) => {
      set(() => ({
        currentMessageId: s,
      }));
    },
    isGeneratedTitle: false,
    setIsGeneratedTitle: (b: boolean) => {
      set(() => ({
        isGeneratedTitle: b,
      }));
    },
    getPostedModel: () => {
      return (
        get().chats[get().conversationId]?.system?.model ??
        // 画面に即時反映するためNEW_MESSAGEを評価
        get().chats['']?.[NEW_MESSAGE_ID.ASSISTANT]?.model
      );
    },
    shouldUpdateMessages: (currentConversation) => {
      return (
        !!get().conversationId &&
        currentConversation.id === get().conversationId &&
        !(
          get().postingMessage &&
          get().postingConversationId === currentConversation.id
        ) &&
        get().currentMessageId !== currentConversation.lastMessageId
      );
    },
    getShouldContinue: () => {
      return get().shouldCotinue;
    },
    setShouldContinue: (b) => {
      set(() => ({
        shouldCotinue: b,
      }));
    },
    shouldCotinue: false,
    reasoningEnabled: false,
    setReasoningEnabled: (enabled) => set({ reasoningEnabled: enabled }),
  };
});

/**
 * Lightweight accessors for components that only need the current conversation.
 * useChat() also creates a streaming actor and data subscriptions.
 */
export const useChatConversationId = () =>
  useChatState((state) => state.conversationId);
export const useSetChatConversationId = () =>
  useChatState((state) => state.setConversationId);
export const useIsGeneratedTitle = () =>
  useChatState((state) => state.isGeneratedTitle);
export const useNewChatCount = () =>
  useChatState((state) => state.newChatCount);
/** Drop the messages of every conversation, for example when the user signs out. */
export const clearChats = () => useChatState.setState({ chats: {} });
export const useNewChat = () => {
  const setConversationId = useChatState((state) => state.setConversationId);
  const setMessages = useChatState((state) => state.setMessages);
  return useCallback(() => {
    useChatState.setState((state) => ({ newChatCount: state.newChatCount + 1 }));
    setConversationId('');
    setMessages('', {});
  }, [setConversationId, setMessages]);
};

const useChat = () => {
  const { open: openSnackbar } = useSnackbar();
  const streamingActor = useActorRef(streamingStateMachine);
  const streamingSend = streamingActor.send;
  // Select only what the page renders. Streamed text is applied through
  // subscribeStreamingText, so text events do not re-render the page.
  const streamingValue = useSelector(streamingActor, (s) => s.value);
  const streamingReasoning = useSelector(streamingActor, (s) => s.context.reasoning);
  const streamingTools = useSelector(streamingActor, (s) => s.context.tools);
  const streamingRelatedDocuments = useSelector(
    streamingActor,
    (s) => s.context.relatedDocuments
  );
  const streamingState = useMemo(
    () => ({
      value: streamingValue,
      context: {
        reasoning: streamingReasoning,
        tools: streamingTools,
        relatedDocuments: streamingRelatedDocuments,
      },
    }),
    [streamingValue, streamingReasoning, streamingTools, streamingRelatedDocuments]
  );

  const {
    chats,
    conversationId,
    setConversationId,
    postingMessage,
    postingConversationId,
    setPostingMessage,
    setMessages,
    pushMessage,
    editMessage,
    copyMessages,
    removeMessage,
    getMessages,
    currentMessageId,
    setCurrentMessageId,
    isGeneratedTitle,
    setIsGeneratedTitle,
    getPostedModel,
    shouldUpdateMessages,
    getShouldContinue,
    setShouldContinue,
    reasoningEnabled,
    setReasoningEnabled,
  } = useChatState();

  const { post: postStreaming } = usePostMessageStreaming();
  const { modelId, setModelId, availableModels } = useModel();

  const conversationApi = useConversationApi();
  const feedbackApi = useFeedbackApi();
  const {
    data,
    mutate,
    isLoading: loadingConversation,
    error: conversationError,
  } = conversationApi.getConversation(conversationId);
  const { syncConversations } = useConversation();

  const {
    data: relatedDocuments,
    mutate: reloadRelatedDocuments,
    isLoading: loadingRelatedDocuments,
    error: relatedDocumentsError,
  } = conversationApi.getRelatedDocuments(conversationId);

  const messages = useMemo(() => {
    return getMessages(conversationId, currentMessageId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId, chats, currentMessageId]);

  const newChat = useNewChat();

  // when updated messages
  useEffect(() => {
    if (data && shouldUpdateMessages(data)) {
      setMessages(conversationId, data.messageMap);
      setCurrentMessageId(data.lastMessageId);
      setModelId(getPostedModel());
      reloadRelatedDocuments();
    }
    if (data && data.shouldContinue !== getShouldContinue()) {
      setShouldContinue(data.shouldContinue);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId, data]);

  useEffect(() => {
    setIsGeneratedTitle(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  const supportReasoning = useMemo(() => {
    // If existing conversation data, use that model
    const postedModel = getPostedModel();
    // Before data is obtained, use the currently selected model
    const effectiveModel = postedModel || modelId;
    // Check if the model supports reasoning
    return availableModels.some(
      (m) => m.modelId === effectiveModel && m.supportReasoning
    );
  }, [modelId, availableModels, getPostedModel]);

  useEffect(() => {
    // If the model does not support reasoning, disable reasoning
    if (!supportReasoning) {
      setReasoningEnabled(false);
    }
  }, [supportReasoning, setReasoningEnabled]);

  // 画面に即時反映させるために、Stateを更新する処理
  const pushNewMessage = (
    parentMessageId: string | null,
    messageContent: MessageContent
  ) => {
    pushMessage(
      conversationId ?? '',
      parentMessageId,
      NEW_MESSAGE_ID.USER,
      messageContent
    );
    pushMessage(
      conversationId ?? '',
      NEW_MESSAGE_ID.USER,
      NEW_MESSAGE_ID.ASSISTANT,
      {
        role: 'assistant',
        content: [
          {
            contentType: 'text',
            body: '',
          },
        ],
        model: messageContent.model,
        feedback: messageContent.feedback,
        usedChunks: messageContent.usedChunks,
        thinkingLog: messageContent.thinkingLog,
      }
    );
  };

  const postChat = (params: {
    content: string;
    enableReasoning: boolean;
    base64EncodedImages?: string[];
    attachments?: AttachmentType[];
    bot?: BotInputType;
  }) => {
    const { content, bot, base64EncodedImages, attachments } = params;
    const isNewChat = conversationId ? false : true;
    const newConversationId = ulid();

    // エラーリトライ時に同期が間に合わないため、Stateを直接参照
    const tmpMessages = convertMessageMapToArray(
      useChatState.getState().chats[conversationId] ?? {},
      currentMessageId
    );

    const parentMessageId = isNewChat
      ? 'system'
      : tmpMessages[tmpMessages.length - 1].id;

    const modelToPost = isNewChat ? modelId : getPostedModel();
    const imageContents: MessageContent['content'] = (
      base64EncodedImages ?? []
    ).map((encodedImage) => {
      const result =
        /data:(?<mediaType>image\/.+);base64,(?<encodedImage>.+)/.exec(
          encodedImage
        );

      return {
        body: result!.groups!.encodedImage,
        contentType: 'image',
        mediaType: result!.groups!.mediaType,
      };
    });

    const attachContents: MessageContent['content'] = (attachments ?? []).map(
      (attachment) => {
        return {
          body: attachment.extractedContent,
          contentType: 'attachment',
          mediaType: attachment.fileType,
          fileName: attachment.fileName,
        };
      }
    );

    const messageContent: MessageContent = {
      content: [
        ...attachContents,
        ...imageContents,
        {
          body: content,
          contentType: 'text',
        },
      ],
      model: modelToPost,
      role: 'user',
      feedback: null,
      usedChunks: null,
      thinkingLog: null,
    };
    const input: PostMessageRequest = {
      conversationId: isNewChat ? newConversationId : conversationId,
      message: {
        ...messageContent,
        parentMessageId: parentMessageId,
      },
      botId: bot?.botId,
      enableReasoning: params.enableReasoning,
    };
    const newChatCount = useChatState.getState().newChatCount;
    const createNewConversation = () => {
      // Copy State to prevent screen flicker
      copyMessages('', newConversationId);

      conversationApi
        .updateTitleWithGeneratedTitle(newConversationId)
        // The conversation exists without a generated title.
        .catch((e) => console.error(e))
        .then(() => {
          // Open the new conversation only if the user is still on this new chat.
          const state = useChatState.getState();
          if (
            state.conversationId === '' &&
            state.newChatCount === newChatCount
          ) {
            setConversationId(newConversationId);
          }
        })
        .finally(() => {
          syncConversations().then(() => {
            setIsGeneratedTitle(true);
          });
        });
    };

    setPostingMessage(true);

    // Update State for immediate reflection on screen
    pushNewMessage(parentMessageId, messageContent);

    // post message
    const postPromise = new Promise<void>((resolve, reject) => {
      if (USE_STREAMING) {
        const unsubscribe = subscribeStreamingText(streamingActor, (text) => {
          editMessage(conversationId, NEW_MESSAGE_ID.ASSISTANT, text);
        });
        postStreaming({
          input,
          handleStreamingEvent: (event) => {
            streamingSend(event);
          },
        })
          .then(() => {
            resolve();
          })
          .catch((e) => {
            reject(e);
          })
          .finally(() => {
            unsubscribe();
          });
      } else {
        conversationApi
          .postMessage(input)
          .then((res) => {
            const textBody = getTextContentBody(res.data.message.content);
            editMessage(conversationId, NEW_MESSAGE_ID.ASSISTANT, textBody);
            resolve();
          })
          .catch((e) => {
            reject(e);
          });
      }
    });

    postPromise
      .then(() => {
        if (isNewChat) {
          createNewConversation();
        } else {
          mutate();
        }
      })
      .catch((e) => {
        console.error(e);
        removeMessage(conversationId, NEW_MESSAGE_ID.ASSISTANT);
      })
      .finally(() => {
        setPostingMessage(false);
      });
  };

  /**
   * Continue to generate
   */
  const continueGenerate = (params?: {
    messageId?: string;
    bot?: BotInputType;
  }) => {
    setPostingMessage(true);

    const messageContent: MessageContent = {
      content: [],
      model: getPostedModel(),
      role: 'user',
      feedback: null,
      usedChunks: null,
      thinkingLog: null,
    };
    const input: PostMessageRequest = {
      conversationId: conversationId,
      message: {
        ...messageContent,
        parentMessageId: messages[messages.length - 1].id,
      },
      botId: params?.bot?.botId,
      continueGenerate: true,
      enableReasoning: false,
    };

    const lastMessage = messages[messages.length - 1];
    const currentContentBody = getTextContentBody(lastMessage.content);
    const currentMessage = messages[messages.length - 1];

    // WARNING: Non-streaming is not supported from the UI side as it is planned to be DEPRICATED.
    const unsubscribe = subscribeStreamingText(streamingActor, (text) => {
      editMessage(conversationId, currentMessage.id, currentContentBody + text);
    });
    postStreaming({
      input,
      handleStreamingEvent: (event) => {
        streamingSend(event);
      },
    })
      .then(() => {
        mutate();
      })
      .catch((e) => {
        console.error(e);
        // The streaming hook rejects with the message to show.
        openSnackbar(
          typeof e === 'string' ? e : i18next.t('error.answerResponse')
        );
        // Drop the partial text and show the saved answer.
        mutate();
      })
      .finally(() => {
        unsubscribe();
        setPostingMessage(false);
      });
  };

  /**
   * 再生成
   * @param props content: 内容を上書きしたい場合に設定  messageId: 再生成対象のmessageId  botId: ボットの場合は設定する
   */
  const regenerate = (props?: {
    enableReasoning: boolean;
    content?: string;
    messageId?: string;
    bot?: BotInputType;
  }) => {
    let index: number = -1;
    // messageIdが指定されている場合は、指定されたメッセージをベースにする
    if (props?.messageId) {
      index = messages.findIndex((m) => m.id === props.messageId);
    }

    // 最新のメッセージがUSERの場合は、エラーとして処理する
    const isRetryError = messages[messages.length - 1].role === 'user';
    // messageIdが指定されていない場合は、最新のメッセージを再生成する
    if (index === -1) {
      index = isRetryError ? messages.length - 1 : messages.length - 2;
    }

    const parentMessage = produce(messages[index], (draft) => {
      if (props?.content) {
        const textIndex = draft.content.findIndex(
          (content) => content.contentType === 'text'
        );
        if (textIndex >= 0) {
          (draft.content[textIndex] as TextContent).body = props.content;
        }
      }
    });

    // Stateを書き換え後の内容に更新
    if (props?.content) {
      editMessage(conversationId, parentMessage.id, props.content);
    }

    const input: PostMessageRequest = {
      conversationId: conversationId,
      message: {
        ...parentMessage,
        parentMessageId: parentMessage.parent,
      },
      botId: props?.bot?.botId,
      enableReasoning: props?.enableReasoning ?? false,
    };

    if (input.message.parentMessageId === null) {
      input.message.parentMessageId = 'system';
    }

    setPostingMessage(true);

    // 画面に即時反映するために、Stateを更新する
    if (isRetryError) {
      pushMessage(
        conversationId ?? '',
        parentMessage.id,
        NEW_MESSAGE_ID.ASSISTANT,
        {
          role: 'assistant',
          content: [
            {
              contentType: 'text',
              body: '',
            },
          ],
          model: messages[index].model,
          feedback: messages[index].feedback,
          usedChunks: messages[index].usedChunks,
          thinkingLog: messages[index].thinkingLog,
        }
      );
    } else {
      pushNewMessage(parentMessage.parent, parentMessage);
    }

    setCurrentMessageId(NEW_MESSAGE_ID.ASSISTANT);

    const unsubscribe = subscribeStreamingText(streamingActor, (text) => {
      editMessage(conversationId, NEW_MESSAGE_ID.ASSISTANT, text);
    });
    postStreaming({
      input,
      handleStreamingEvent: (event) => {
        streamingSend(event);
      },
    })
      .then(() => {
        mutate();
      })
      .catch((e) => {
        console.error(e);
        setCurrentMessageId(NEW_MESSAGE_ID.USER);
        removeMessage(conversationId, NEW_MESSAGE_ID.ASSISTANT);
      })
      .finally(() => {
        unsubscribe();
        setPostingMessage(false);
      });
  };

  const hasError = useMemo(() => {
    const length_ = messages.length;
    return length_ === 0 ? false : messages[length_ - 1].role === 'user';
  }, [messages]);

  return {
    streamingState,
    hasError,
    setConversationId,
    conversationId,
    loadingConversation,
    conversationError,
    postingMessage: postingMessage || loadingConversation,
    // Whether the message being posted belongs to the shown conversation.
    isStreamingHere: postingMessage && postingConversationId === conversationId,
    isGeneratedTitle,
    setIsGeneratedTitle,
    newChat,
    messages,
    setCurrentMessageId,
    postChat,
    regenerate,
    getPostedModel,
    getShouldContinue,
    continueGenerate,
    reasoningEnabled,
    setReasoningEnabled,
    supportReasoning,
    // エラーのリトライ
    retryPostChat: (params: {
      enableReasoning: boolean;
      content?: string;
      bot?: BotInputType;
    }) => {
      const length_ = messages.length;
      if (length_ === 0) {
        return;
      }
      const latestMessage = messages[length_ - 1];
      if (latestMessage.sibling.length === 1) {
        // 通常のメッセージ送信時
        // エラー発生時の最新のメッセージはユーザ入力;
        removeMessage(conversationId, latestMessage.id);

        const latestMessageBody = getTextContentBody(latestMessage.content);
        // Send the images and attachments of the removed message again.
        const base64EncodedImages = latestMessage.content
          .filter((c): c is ImageContent => c.contentType === 'image')
          .map((c) => `data:${c.mediaType};base64,${c.body}`);
        const attachments = latestMessage.content
          .filter(
            (c): c is AttachmentContent => c.contentType === 'attachment'
          )
          .map((c) => ({
            fileName: c.fileName ?? '',
            // The backend does not read the media type of attachments.
            fileType: '',
            extractedContent: c.body,
          }));
        postChat({
          content: params.content ?? latestMessageBody,
          base64EncodedImages,
          attachments,
          enableReasoning: params.enableReasoning,
          bot: params.bot
            ? {
                botId: params.bot.botId,
                hasKnowledge: params.bot.hasKnowledge,
                hasAgent: params.bot.hasAgent,
              }
            : undefined,
        });
      } else {
        // 再生成時
        const latestMessageBody = getTextContentBody(latestMessage.content);
        regenerate({
          enableReasoning: params.enableReasoning,
          content: params.content ?? latestMessageBody,
          bot: params.bot,
        });
      }
    },
    relatedDocuments,
    reloadRelatedDocuments,
    loadingRelatedDocuments,
    relatedDocumentsError,
    giveFeedback: (messageId: string, feedback: PutFeedbackRequest) => {
      return feedbackApi
        .putFeedback(conversationId, messageId, feedback)
        .then(() => {
          mutate();
        });
    },
  };
};

export default useChat;
