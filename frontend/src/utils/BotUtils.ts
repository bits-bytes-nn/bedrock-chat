import { BotFile, SharedScope } from '../@types/bot';
import copy from 'copy-to-clipboard';
import {
  convertedFileName,
  isConvertibleFile,
} from '../constants/supportedAttachedFiles';

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

/**
 * Removes a row of the knowledge file uploader
 * @param files Rows of the uploader
 * @param uid Id of the row to remove
 * @returns The remaining rows and the name of the bot file to delete, which is
 * undefined when the row was rejected before the upload
 */
export const removeBotFile = (
  files: BotFile[],
  uid: string
): { files: BotFile[]; deletedFilename?: string } => {
  const removed = files.find((f) => f.uid === uid);
  return {
    files: files.filter((f) => f.uid !== uid),
    deletedFilename:
      removed && !removed.rejected ? removed.filename : undefined,
  };
};

// A converted file is registered as `<filename>.txt`.
const registeredNames = (filename: string): string[] =>
  isConvertibleFile(filename)
    ? [filename, convertedFileName(filename)]
    : [filename];

/**
 * Whether a file would be registered under the name of another row, such as
 * `deck.pptx.txt` next to `deck.pptx`, which is converted to that name
 * @param filename Name of the file to add
 * @param files Rows of the uploader, including the files added before it
 */
export const isDuplicateBotFile = (
  filename: string,
  files: BotFile[]
): boolean => {
  const names = registeredNames(filename);
  return files.some(
    (file) =>
      !file.rejected &&
      registeredNames(file.filename).some((name) => names.includes(name))
  );
};
