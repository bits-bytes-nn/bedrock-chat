import { isAxiosError } from 'axios';
import i18next from 'i18next';

/**
 * Return the message of a backend error response, if it has one. Errors with a
 * known `code` are translated; others keep the backend's English message.
 */
export const getApiErrorMessage = (error: unknown): string | undefined => {
  if (!isAxiosError(error)) {
    return undefined;
  }
  // The API returns {"errors": [...]}; FastAPI checks return {"detail": "..."}.
  const data = error.response?.data;
  const key = `error.api.${data?.code}`;
  if (typeof data?.code === 'string' && i18next.exists(key)) {
    return i18next.t(key, data.params ?? {});
  }
  const message = data?.errors?.[0] ?? data?.detail;
  return typeof message === 'string' ? message : undefined;
};

/** Return the HTTP status of a failed API request, if it has one. */
export const getApiErrorStatus = (error: unknown): number | undefined =>
  isAxiosError(error) ? error.response?.status : undefined;
