export type ResizedImageMediaType = 'image/png' | 'image/jpeg';

// Quality of the JPEG that a resized image is encoded to.
export const RESIZED_JPEG_QUALITY = 0.9;

/**
 * The media type that a resized image is encoded to. PNG stays PNG, which keeps
 * text and screenshots sharp; other images become JPEG, which is much smaller
 * for photos. Both are drawn on white, so transparent areas never turn black.
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

/**
 * The images to attach from a paste. Office apps, spreadsheets and web pages
 * put a picture of the selection next to its text, so a paste with text pastes
 * the text, and only a paste of just an image, such as a screenshot, attaches it.
 *
 * @param clipboardData The clipboard data of the paste event.
 * @param supportedMediaTypes The image media types that the model accepts.
 */
export const getPastedImages = (
  clipboardData: Pick<DataTransfer, 'getData' | 'items'>,
  supportedMediaTypes: string[]
): File[] => {
  if (clipboardData.getData('text/plain').trim()) {
    return [];
  }
  return Array.from(clipboardData.items)
    .filter((item) => supportedMediaTypes.includes(item.type))
    .map((item) => item.getAsFile())
    .filter((file): file is File => file !== null);
};
