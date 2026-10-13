import { AxiosError, AxiosHeaders } from 'axios';
import { describe, expect, it } from 'vitest';
import { getApiErrorMessage, getApiErrorStatus } from '../ErrorUtils';

const apiError = (data: unknown) =>
  new AxiosError('Request failed', '403', undefined, undefined, {
    data,
    status: 403,
    statusText: 'Forbidden',
    headers: {},
    config: { headers: new AxiosHeaders() },
  });

describe('getApiErrorMessage', () => {
  it('reads the app and FastAPI error formats', () => {
    expect(getApiErrorMessage(apiError({ errors: ['Bot ID must be a ULID.'] }))).toBe(
      'Bot ID must be a ULID.'
    );
    expect(getApiErrorMessage(apiError({ detail: 'User is not allowed to create bot.' }))).toBe(
      'User is not allowed to create bot.'
    );
  });

  it('ignores validation details and other errors', () => {
    expect(getApiErrorMessage(apiError({ detail: [{ msg: 'invalid' }] }))).toBeUndefined();
    expect(getApiErrorMessage(new Error('network'))).toBeUndefined();
  });
});

describe('getApiErrorStatus', () => {
  it('returns the status of an API error only', () => {
    expect(getApiErrorStatus(apiError({}))).toBe(403);
    expect(getApiErrorStatus(new Error('network'))).toBeUndefined();
  });
});
