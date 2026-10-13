import { describe, expect, it } from 'vitest';
import { BotFile } from '../../@types/bot';
import { removeBotFile } from '../BotUtils';

const uploaded: BotFile = { uid: '1', filename: 'a.pdf', status: 'UPLOADED' };
const duplicate: BotFile = {
  uid: '2',
  filename: 'a.pdf',
  status: 'ERROR',
  rejected: true,
};
const failed: BotFile = { uid: '3', filename: 'b.pdf', status: 'ERROR' };

describe('removeBotFile', () => {
  it('keeps the bot file when its rejected duplicate row is removed', () => {
    expect(removeBotFile([uploaded, duplicate], '2')).toEqual({
      files: [uploaded],
      deletedFilename: undefined,
    });
  });

  it('deletes the bot file when its row is removed', () => {
    expect(removeBotFile([uploaded, duplicate], '1')).toEqual({
      files: [duplicate],
      deletedFilename: 'a.pdf',
    });
  });

  it('deletes the file of a failed upload', () => {
    expect(removeBotFile([uploaded, failed], '3')).toEqual({
      files: [uploaded],
      deletedFilename: 'b.pdf',
    });
  });
});
