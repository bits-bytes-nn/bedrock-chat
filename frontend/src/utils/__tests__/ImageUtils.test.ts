import { describe, expect, test } from 'vitest';
import { getResizedImageMediaType } from '../ImageUtils';

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
