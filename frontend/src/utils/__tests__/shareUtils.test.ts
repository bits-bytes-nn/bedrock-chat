import i18next from 'i18next';
import { beforeAll, describe, expect, test } from 'vitest';
import en from '../../i18n/en';
import { getShareText } from '../shareUtils';

describe('getShareText', () => {
  beforeAll(async () => {
    await i18next.init({ lng: 'en', resources: { en } });
  });

  test.each([
    [0, 0, 'Not shared with any groups or users'],
    [1, 0, 'Shared with 1 user'],
    [2, 0, 'Shared with 2 users'],
    [0, 1, 'Shared with 1 group'],
    [0, 3, 'Shared with 3 groups'],
    [1, 1, 'Shared with 1 group and 1 user'],
    [2, 1, 'Shared with 1 group and 2 users'],
    [1, 2, 'Shared with 2 groups and 1 user'],
    [2, 2, 'Shared with 2 groups and 2 users'],
  ])('users=%i groups=%i', (users, groups, expected) => {
    expect(getShareText(users, groups)).toBe(expected);
  });
});
