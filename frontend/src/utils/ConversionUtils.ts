export type ConversionStatus = {
  status: 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';
  reason: string;
};

const POLL_INTERVAL_MS = 5000;
// Transcribe usually finishes within a fraction of the recording's length.
const TIMEOUT_MS = 60 * 60 * 1000;
// A poll can fail transiently while the conversion keeps running.
const MAX_CONSECUTIVE_POLL_ERRORS = 3;

const sleep = (ms: number) =>
  new Promise<void>((resolve) => setTimeout(resolve, ms));

export class ConversionCanceledError extends Error {}

/**
 * Poll a conversion until it completes. Throws if it fails, times out or is
 * aborted.
 */
export const waitForConversion = async <T extends ConversionStatus>(
  first: T,
  fetchStatus: () => Promise<T>,
  options: {
    signal?: AbortSignal;
    sleep?: (ms: number) => Promise<void>;
    intervalMs?: number;
    timeoutMs?: number;
  } = {}
): Promise<T> => {
  const {
    signal,
    sleep: wait = sleep,
    intervalMs = POLL_INTERVAL_MS,
    timeoutMs = TIMEOUT_MS,
  } = options;
  let status = first;
  let waited = 0;
  let errors = 0;
  while (status.status === 'IN_PROGRESS') {
    if (waited >= timeoutMs) {
      throw new Error('The conversion timed out.');
    }
    await wait(intervalMs);
    waited += intervalMs;
    if (signal?.aborted) {
      throw new ConversionCanceledError();
    }
    try {
      status = await fetchStatus();
      errors = 0;
    } catch (e) {
      errors += 1;
      if (errors >= MAX_CONSECUTIVE_POLL_ERRORS) {
        throw e;
      }
    }
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
