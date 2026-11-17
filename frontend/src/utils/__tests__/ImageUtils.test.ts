import { describe, expect, test } from 'vitest';
import { getPastedImages, getResizedImageMediaType } from '../ImageUtils';

describe('getResizedImageMediaType', () => {
  test.each([
    ['image/png', 'a.png', 'image/png'],
    ['IMAGE/PNG', 'a', 'image/png'],
    ['image/jpeg', 'a.jpg', 'image/jpeg'],
    ['image/webp', 'a.webp', 'image/jpeg'],
    ['image/gif', 'a.gif', 'image/jpeg'],
    // The media type wins over the file name.
    ['image/jpeg', 'a.png', 'image/jpeg'],
  ])('%s %s -> %s', (mediaType, fileName, expected) => {
    expect(getResizedImageMediaType(mediaType, fileName)).toBe(expected);
  });

  test('uses the file name when the media type is empty', () => {
    expect(getResizedImageMediaType('', 'Screenshot.PNG')).toBe('image/png');
    expect(getResizedImageMediaType('', 'photo.heic')).toBe('image/jpeg');
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
