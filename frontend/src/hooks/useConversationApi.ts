import { MutatorCallback, useSWRConfig } from 'swr';
import {
  Conversation,
  ConversationMeta,
  PostMessageRequest,
  PostMessageResponse,
  RelatedDocument,
} from '../@types/conversation';
import useHttp from './useHttp';

const useConversationApi = () => {
  const http = useHttp();
  const { mutate } = useSWRConfig();

  const updateTitle = (conversationId: string, title: string) => {
    return http.patch(`conversation/${conversationId}/title`, {
      newTitle: title,
    });
  };

  return {
    getConversations: () => {
      return http.get<ConversationMeta[]>('conversations', {
        keepPreviousData: true,
      });
    },
    getConversation: (conversationId?: string) => {
      return http.get<Conversation>(
        !conversationId ? null : `conversation/${conversationId}`,
        {
          // useChat ignores the previous conversation while the next one loads.
          keepPreviousData: true,
          // Refetching the whole conversation on every focus is costly. The app
          // revalidates it after posting and on opening it again.
          revalidateOnFocus: false,
        }
      );
    },
    postMessage: (input: PostMessageRequest) => {
      return http.post<PostMessageResponse>('conversation', {
        ...input,
      });
    },
    getRelatedDocuments: (conversationId?: string) => {
      return http.get<RelatedDocument[]>(
        // Not keepPreviousData: the documents have no conversation ID, so those of
        // the previous conversation could be shown in a new chat.
        !conversationId ? null : `conversation/${conversationId}/related-documents`
      );
    },
    getRelatedDocument: async (conversationId: string, sourceId: string) => {
      const res = await http.getOnce<RelatedDocument>(`conversation/${conversationId}/related-documents/${sourceId}`);
      return res.data;
    },
    deleteConversation: (conversationId: string) => {
      return http.delete(`conversation/${conversationId}`);
    },
    clearConversations: () => {
      return http.delete('conversations');
    },
    updateTitle,
    updateTitleWithGeneratedTitle: async (conversationId: string) => {
      const res = await http.getOnce<{
        title: string;
      }>(`conversation/${conversationId}/proposed-title`);
      return updateTitle(conversationId, res.data.title);
    },
    /** Refetch a conversation, also when another one is shown. */
    refetchConversation: (conversationId: string) =>
      mutate<Conversation>(`conversation/${conversationId}`),
    mutateConversations: (
      conversations?:
        | ConversationMeta[]
        | Promise<ConversationMeta[]>
        | MutatorCallback<ConversationMeta[]>,
      options?: Parameters<typeof mutate>[2]
    ) => {
      return mutate('conversations', conversations, options);
    },
  };
};

export default useConversationApi;
