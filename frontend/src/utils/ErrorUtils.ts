import { isAxiosError } from 'axios';
import i18next from 'i18next';

/**
 * Whether the UI is shown in English. The backend writes its messages in
 * English, so only English users see a backend message without a known code;
 * other users see a translated fallback instead.
 */
export const isEnglishLanguage = (): boolean =>
  i18next.language?.startsWith('en') ?? false;

/** Return the `code` of a backend error response, if it has one. */
export const getApiErrorCode = (error: unknown): string | undefined => {
  const code = isAxiosError(error) ? error.response?.data?.code : undefined;
  return typeof code === 'string' ? code : undefined;
};

/**
 * Return the message of a backend error response, if it has one.
 *
 * Errors with a known `code` are translated. Other backend messages are
 * returned only for English; for other languages this returns undefined, so
 * the caller shows its translated fallback.
 */
export const getApiErrorMessage = (error: unknown): string | undefined => {
  if (!isAxiosError(error)) {
    return undefined;
  }
  // The API returns {"errors": [...]}; FastAPI checks return {"detail": "..."}.
  const data = error.response?.data;
  const code = getApiErrorCode(error);
  const key = `error.api.${code}`;
  if (code !== undefined && i18next.exists(key)) {
    return i18next.t(key, data.params ?? {});
  }
  if (!isEnglishLanguage()) {
    return undefined;
  }
  const message = data?.errors?.[0] ?? data?.detail;
  return typeof message === 'string' ? message : undefined;
};

/**
 * Whether the bot is not published. Only the code tells, because a 404 also means
 * a deleted bot or a missing build.
 */
export const isBotNotPublishedError = (error: unknown): boolean =>
  getApiErrorCode(error) === 'bot_not_published';
