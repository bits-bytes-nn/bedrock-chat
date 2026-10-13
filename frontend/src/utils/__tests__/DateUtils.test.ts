import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { toUtcDateHour } from '../DateUtils';

// CI runs in UTC, where a missing conversion would go unnoticed, so the test uses
// a zone with an offset. Node applies TZ changes to later Date operations.
const originalTimeZone = process.env.TZ;
beforeAll(() => {
  process.env.TZ = 'Asia/Seoul';
});
afterAll(() => {
  process.env.TZ = originalTimeZone;
});

describe('toUtcDateHour', () => {
  it('converts the hours of a local day to the UTC hours of the partitions', () => {
    expect(toUtcDateHour('20261014', 0, 'YYYYMMDD')).toBe('2026101315');
    expect(toUtcDateHour('20261014', 23, 'YYYYMMDD')).toBe('2026101414');
  });

  it('returns nothing for an invalid date', () => {
    expect(toUtcDateHour('2026-10-14', 0, 'YYYYMMDD')).toBeUndefined();
  });
});
