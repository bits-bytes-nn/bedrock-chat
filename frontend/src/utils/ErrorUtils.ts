import { isAxiosError } from 'axios';

/** Return the message of a backend error response, if it has one. */
export const getApiErrorMessage = (error: unknown): string | undefined => {
  if (!isAxiosError(error)) {
    return undefined;
  }
  // The API returns {"errors": [...]}; FastAPI checks return {"detail": "..."}.
  const data = error.response?.data;
  const message = data?.errors?.[0] ?? data?.detail;
  return typeof message === 'string' ? message : undefined;
};

/** Return the HTTP status of a failed API request, if it has one. */
export const getApiErrorStatus = (error: unknown): number | undefined =>
  isAxiosError(error) ? error.response?.status : undefined;
