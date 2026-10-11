import { SharedScope } from '../@types/bot';
import copy from 'copy-to-clipboard';

export const getBotUrl = (botId: string) => {
  return `${window.location.origin}/bot/${botId}`;
};

export const copyBotUrl = (botId: string) => {
  copy(getBotUrl(botId));
};

/**
 * Determines if a bot is pinned by an administrator
 * @param botSharedStatus Bot shared status
 * @returns true if the bot is pinned, false otherwise
 */
export const isPinnedBot = (botSharedStatus: string): boolean => {
  return botSharedStatus.startsWith('pinned@');
};

/**
 * Determines if a bot can be pinned by an administrator
 * @param bot Bot metadata
 * @returns true if the bot can be pinned, false otherwise
 */
export const canBePinned = (botSharedScope: SharedScope): boolean => {
  return botSharedScope === 'all';
};
