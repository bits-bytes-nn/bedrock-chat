import { describe, expect, it } from 'vitest';
import { BotFile } from '../../@types/bot';
import { isDuplicateBotFile, removeBotFile } from '../BotUtils';

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

describe('isDuplicateBotFile', () => {
  const row = (filename: string, rejected = false): BotFile => ({
    uid: filename,
    filename,
    status: 'UPLOADED',
    rejected,
  });

  it('finds the converted name in both directions', () => {
    expect(isDuplicateBotFile('deck.pptx.txt', [row('deck.pptx')])).toBe(true);
    expect(isDuplicateBotFile('deck.pptx', [row('deck.pptx.txt')])).toBe(true);
  });

  it('finds the same name and ignores rejected rows', () => {
    expect(isDuplicateBotFile('a.pdf', [row('a.pdf')])).toBe(true);
    expect(isDuplicateBotFile('a.pdf', [row('a.pdf', true)])).toBe(false);
    expect(isDuplicateBotFile('b.pdf', [row('a.pdf')])).toBe(false);
  });
});
