import { useState } from 'react';
import { UpdateBotPushedRequest } from '../@types/bot';
import { useTranslation } from 'react-i18next';
import useAdminApi from './useAdminApi';
import useSnackbar from './useSnackbar';
import { getApiErrorMessage } from '../utils/ErrorUtils';

const useBotPinning = () => {
  const adminApi = useAdminApi();
  const { t } = useTranslation();
  const { open } = useSnackbar();
  const [isUpdating, setIsUpdating] = useState(false);

  /**
   * Register a bot as pinned by administrator
   */
  const pinBot = async (botId: string, order: number) => {
    setIsUpdating(true);
    try {
      const params: UpdateBotPushedRequest = {
        toPinned: true,
        order,
      };
      await adminApi.updatePinnedBot(botId, params);
      return true;
    } catch (error) {
      console.error('Failed to mark bot as essential:', error);
      open(getApiErrorMessage(error) ?? t('bot.error.failUpdateEssential'));
      return false;
    } finally {
      setIsUpdating(false);
    }
  };

  /**
   * Remove pinned status from a bot
   */
  const unpinBot = async (botId: string) => {
    setIsUpdating(true);
    try {
      const params: UpdateBotPushedRequest = {
        toPinned: false,
      };
      await adminApi.updatePinnedBot(botId, params);
      return true;
    } catch (error) {
      console.error('Failed to remove essential status:', error);
      open(getApiErrorMessage(error) ?? t('bot.error.failUpdateEssential'));
      return false;
    } finally {
      setIsUpdating(false);
    }
  };

  return {
    pinBot,
    unpinBot,
    isUpdating,
  };
};

export default useBotPinning;
