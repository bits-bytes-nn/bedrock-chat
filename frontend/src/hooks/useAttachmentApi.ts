import axios from 'axios';
import useHttp from './useHttp';
import { ConversionStatus, waitForConversion } from '../utils/ConversionUtils';

type AttachmentUploadResponse = { uploadId: string; url: string };
type AttachmentConversionResponse = ConversionStatus & { text: string | null };

/** Chat attachments that are converted to text before they are sent. */
const useAttachmentApi = () => {
  const http = useHttp();

  return {
    /** Upload the file, convert it and return the text. */
    convertToText: async (
      file: File,
      signal?: AbortSignal
    ): Promise<string> => {
      const {
        data: { uploadId, url },
      } = await http.getOnce<AttachmentUploadResponse>(
        'attachments/presigned-url',
        { filename: file.name, contentType: file.type }
      );
      // The presigned URL contains the credentials.
      await axios.put(url, file, {
        headers: { 'Content-Type': file.type },
        signal,
      });
      const conversionUrl = `attachments/${uploadId}/conversion`;
      const started = await http.post<AttachmentConversionResponse>(
        `${conversionUrl}?filename=${encodeURIComponent(file.name)}`,
        {}
      );
      const result = await waitForConversion(
        started.data,
        () =>
          http
            .getOnce<AttachmentConversionResponse>(conversionUrl, {
              filename: file.name,
            })
            .then((res) => res.data),
        { signal }
      );
      return result.text ?? '';
    },
  };
};

export default useAttachmentApi;
