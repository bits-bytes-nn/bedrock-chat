import { describe, expect, test } from 'vitest';
import {
  getPastedImages,
  getResizedImageMediaTypes,
  getSmallestDataUrl,
} from '../ImageUtils';

describe('getResizedImageMediaTypes', () => {
  const BOTH = ['image/png', 'image/jpeg'];
  const JPEG = ['image/jpeg'];
  test.each([
    ['image/png', 'a.png', BOTH],
    ['IMAGE/PNG', 'a', BOTH],
    ['image/jpeg', 'a.jpg', JPEG],
    ['image/webp', 'a.webp', JPEG],
    ['image/gif', 'a.gif', JPEG],
    // The media type wins over the file name.
    ['image/jpeg', 'a.png', JPEG],
  ])('%s %s -> %s', (mediaType, fileName, expected) => {
    expect(getResizedImageMediaTypes(mediaType, fileName)).toEqual(expected);
  });

  test('uses the file name when the media type is empty', () => {
    expect(getResizedImageMediaTypes('', 'Screenshot.PNG')).toEqual(BOTH);
    expect(getResizedImageMediaTypes('', 'photo.heic')).toEqual(JPEG);
  });
});

describe('getSmallestDataUrl', () => {
  test('returns the shortest data URL', () => {
    const png = 'data:image/png;base64,' + 'A'.repeat(100);
    const jpeg = 'data:image/jpeg;base64,' + 'A'.repeat(40);
    expect(getSmallestDataUrl([png, jpeg])).toBe(jpeg);
    expect(getSmallestDataUrl([jpeg, png])).toBe(jpeg);
    expect(getSmallestDataUrl([png])).toBe(png);
  });
});

describe('getPastedImages', () => {
  const PNG = 'image/png';
  const clipboard = (text: string, types: string[]) => {
    const files = types.map((type) => new File(['x'], 'image', { type }));
    return {
      getData: (format: string) => (format === 'text/plain' ? text : ''),
      items: files.map((file) => ({
        type: file.type,
        getAsFile: () => file,
      })) as unknown as DataTransferItemList,
    };
  };

  test('attaches a pasted screenshot', () => {
    expect(getPastedImages(clipboard('', [PNG]), [PNG])).toHaveLength(1);
  });

  test('pastes text when the clipboard also has a picture of it', () => {
    expect(
      getPastedImages(clipboard('Quarterly report', [PNG]), [PNG])
    ).toEqual([]);
  });

  test('ignores whitespace-only text', () => {
    expect(getPastedImages(clipboard(' \n', [PNG]), [PNG])).toHaveLength(1);
  });

  test('skips media types that the model does not accept', () => {
    expect(getPastedImages(clipboard('', ['image/tiff']), [PNG])).toEqual([]);
    expect(getPastedImages(clipboard('', [PNG]), [])).toEqual([]);
  });
});
