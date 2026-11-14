export type ResizedImageMediaType = 'image/png' | 'image/jpeg';

// Quality of the JPEG that a resized image is encoded to.
export const RESIZED_JPEG_QUALITY = 0.9;

/**
 * The media type that a resized image is encoded to. PNG stays PNG to keep its
 * transparency; other images become JPEG, which is much smaller for photos.
 *
 * @param mediaType The media type of the file, which can be empty.
 * @param fileName The file name, used when the media type is empty.
 */
export const getResizedImageMediaType = (
  mediaType: string,
  fileName: string
): ResizedImageMediaType => {
  const isPng = mediaType
    ? mediaType.toLowerCase() === 'image/png'
    : fileName.toLowerCase().endsWith('.png');
  return isPng ? 'image/png' : 'image/jpeg';
};
