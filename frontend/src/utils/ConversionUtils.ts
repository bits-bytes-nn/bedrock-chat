export type ConversionStatus = {
  status: 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';
  reason: string;
};

const POLL_INTERVAL_MS = 5000;
// Transcribe usually finishes within a fraction of the recording's length.
const TIMEOUT_MS = 60 * 60 * 1000;

const sleep = (ms: number) =>
  new Promise<void>((resolve) => setTimeout(resolve, ms));

/** Poll a conversion until it completes. Throws if it fails or times out. */
export const waitForConversion = async <T extends ConversionStatus>(
  first: T,
  fetchStatus: () => Promise<T>,
  options = { sleep, intervalMs: POLL_INTERVAL_MS, timeoutMs: TIMEOUT_MS }
): Promise<T> => {
  let status = first;
  let waited = 0;
  while (status.status === 'IN_PROGRESS') {
    if (waited >= options.timeoutMs) {
      throw new Error('The conversion timed out.');
    }
    await options.sleep(options.intervalMs);
    waited += options.intervalMs;
    status = await fetchStatus();
  }
  if (status.status === 'FAILED') {
    throw new Error(status.reason || 'The conversion failed.');
  }
  return status;
};

export const bytesToBase64 = (bytes: Uint8Array): string => {
  let binary = '';
  // Spread in chunks to avoid `Maximum call stack size exceeded`.
  const chunkSize = 8192;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.slice(i, i + chunkSize));
  }
  return btoa(binary);
};

export const textToBase64 = (text: string): string =>
  bytesToBase64(new TextEncoder().encode(text));
