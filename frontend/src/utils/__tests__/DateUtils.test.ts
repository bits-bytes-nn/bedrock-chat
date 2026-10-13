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
    expect(toUtcDateHour('20261014', 0, 0, 'YYYYMMDD')).toBe('2026101315');
    expect(toUtcDateHour('20261014', 23, 59, 'YYYYMMDD')).toBe('2026101414');
  });

  it('includes the UTC hour of the last minute for a half-hour offset', () => {
    process.env.TZ = 'Asia/Kolkata';
    try {
      // 2026-10-14 00:00 IST is 2026-10-13 18:30 UTC.
      expect(toUtcDateHour('20261014', 0, 0, 'YYYYMMDD')).toBe('2026101318');
      // 23:59 IST is 18:29 UTC, so the last local hour reaches the 18 UTC hour.
      expect(toUtcDateHour('20261014', 23, 59, 'YYYYMMDD')).toBe('2026101418');
    } finally {
      process.env.TZ = 'Asia/Seoul';
    }
  });

  it('returns nothing for an invalid date', () => {
    expect(toUtcDateHour('2026-10-14', 0, 0, 'YYYYMMDD')).toBeUndefined();
  });
});
