import { AxiosError, AxiosHeaders } from 'axios';
import i18next from 'i18next';
import { afterEach, beforeAll, describe, expect, it } from 'vitest';
import en from '../../i18n/en';
import ko from '../../i18n/ko';
import {
  getApiErrorCode,
  getApiErrorMessage,
  isBotNotPublishedError,
} from '../ErrorUtils';

const apiError = (data: unknown, status = 403) =>
  new AxiosError('Request failed', String(status), undefined, undefined, {
    data,
    status,
    statusText: 'Error',
    headers: {},
    config: { headers: new AxiosHeaders() },
  });

beforeAll(async () => {
  await i18next.init({ lng: 'en', fallbackLng: 'en', resources: { en, ko } });
});

afterEach(async () => {
  await i18next.changeLanguage('en');
});

describe('getApiErrorMessage', () => {
  it('reads the app and FastAPI error formats in English', () => {
    expect(getApiErrorMessage(apiError({ errors: ['Bot ID must be a ULID.'] }))).toBe(
      'Bot ID must be a ULID.'
    );
    expect(getApiErrorMessage(apiError({ detail: 'User is not allowed to create bot.' }))).toBe(
      'User is not allowed to create bot.'
    );
    expect(
      getApiErrorMessage(apiError({ errors: ['English'], code: 'unknown_code' }))
    ).toBe('English');
  });

  it('translates errors with a known code', async () => {
    await i18next.changeLanguage('ko');
    expect(
      getApiErrorMessage(
        apiError({
          errors: ['You can have at most 2 bots'],
          code: 'dedicated_knowledge_base_limit',
          params: { limit: 2 },
        })
      )
    ).toContain('최대 2개');
    expect(
      getApiErrorMessage(
        apiError({ errors: ['Bot X is not published.'], code: 'bot_not_published' }, 404)
      )
    ).toBe(ko.translation.error.api.bot_not_published);
  });

  it('hides backend messages without a known code in other languages', async () => {
    await i18next.changeLanguage('ko');
    expect(
      getApiErrorMessage(apiError({ errors: ['English'], code: 'unknown_code' }))
    ).toBeUndefined();
    expect(getApiErrorMessage(apiError({ detail: 'English' }))).toBeUndefined();
  });

  it('ignores validation details and other errors', () => {
    expect(getApiErrorMessage(apiError({ detail: [{ msg: 'invalid' }] }))).toBeUndefined();
    expect(getApiErrorMessage(new Error('network'))).toBeUndefined();
  });
});

describe('getApiErrorCode', () => {
  it('returns a string code of an API error only', () => {
    expect(getApiErrorCode(apiError({ code: 'bot_not_published' }))).toBe(
      'bot_not_published'
    );
    expect(getApiErrorCode(apiError({ code: 1 }))).toBeUndefined();
    expect(getApiErrorCode(apiError(undefined))).toBeUndefined();
    expect(getApiErrorCode(new Error('network'))).toBeUndefined();
  });
});

describe('isBotNotPublishedError', () => {
  it('reads the error code only', () => {
    expect(isBotNotPublishedError(apiError({ code: 'bot_not_published' }, 400))).toBe(true);
    expect(isBotNotPublishedError(apiError({}, 404))).toBe(false);
    expect(isBotNotPublishedError(apiError({ errors: ['Bot X is not published.'] }, 400))).toBe(
      false
    );
    expect(isBotNotPublishedError(undefined)).toBe(false);
  });
});
