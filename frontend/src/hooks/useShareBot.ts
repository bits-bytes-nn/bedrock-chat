import { KeyedMutator } from 'swr';
import useBotApi from './useBotApi';
import { BotListItem, SharedScope } from '../@types/bot';
import { produce } from 'immer';
import { useRef } from 'react';
import { useTranslation } from 'react-i18next';
import useSnackbar from './useSnackbar';
import { getApiErrorMessage } from '../utils/ErrorUtils';

const useShareBot = (
  params: {
    botId?: string;
  } & (
    | {
        myBots: BotListItem[];
        mutateMyBots: KeyedMutator<BotListItem[]>;
      }
    | {
        myBots?: undefined;
        mutateMyBots?: undefined;
      }
  )
) => {
  const { botId, myBots, mutateMyBots } = params;
  const { getMyBot, updateBotSharedScope } = useBotApi();
  const requestIdRef = useRef<number>(0);
  const { t } = useTranslation();
  const { open: openSnackbar } = useSnackbar();
  // The optimistic update is reverted by the refetch after the request.
  const onError = (e: unknown) => {
    console.error(e);
    openSnackbar(getApiErrorMessage(e) ?? t('bot.error.failShare'));
  };

  const { data, isLoading, mutate } = getMyBot(botId);

  return {
    isLoading,
    isPublication: data?.isPublication,
    sharedStatus: data?.sharedStatus,
    sharedScope: data?.sharedScope,
    allowedUserIds: data?.allowedCognitoUsers,
    allowedGroupIds: data?.allowedCognitoGroups,
    updateSharedScope: (sharedScope: SharedScope) => {
      if (!botId) {
        return;
      }

      // Optimistic UI update
      if (mutateMyBots) {
        mutateMyBots(
          produce(myBots, (draft) => {
            const idx = draft.findIndex((bot) => bot.id === botId);
            if (draft) {
              draft[idx].sharedScope = sharedScope;
            }
          }),
          {
            revalidate: false,
          }
        );
      }

      if (data) {
        mutate(
          produce(data, (draft) => {
            draft.sharedScope = sharedScope;
          }),
          {
            revalidate: false,
          }
        );
      }

      // Increment request ID
      const currentRequestId = ++requestIdRef.current;

      return updateBotSharedScope(
        botId,
        sharedScope === 'partial'
          ? {
              targetSharedScope: sharedScope,
              targetAllowedGroupIds: [],
              targetAllowedUserIds: [],
            }
          : {
              targetSharedScope: sharedScope,
            }
      )
        .catch(onError)
        .finally(() => {
          // Only execute mutate for the latest request
          if (currentRequestId === requestIdRef.current) {
            mutateMyBots?.();
            mutate();
          }
        });
    },
    updateSharedUsersAndGroups: (userIds: string[], groupIds: string[]) => {
      if (!botId) {
        return;
      }
      if (!data || data?.sharedScope !== 'partial') {
        throw new Error("SharedScope is not 'partial'");
      }

      mutate(
        produce(data, (draft) => {
          draft.allowedCognitoUsers = userIds;
          draft.allowedCognitoGroups = groupIds;
        }),
        {
          revalidate: false,
        }
      );

      // Increment request ID
      const currentRequestId = ++requestIdRef.current;

      return updateBotSharedScope(botId, {
        targetSharedScope: 'partial',
        targetAllowedGroupIds: groupIds,
        targetAllowedUserIds: userIds,
      })
        .catch(onError)
        .finally(() => {
          // Only execute mutate for the latest request
          if (currentRequestId === requestIdRef.current) {
            mutate();
          }
        });
    },
  };
};

export default useShareBot;
