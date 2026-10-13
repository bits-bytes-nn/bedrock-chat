import { describe, expect, it } from 'vitest';
import { toUtcDateHour } from '../DateUtils';

// The UTC hour of a local time, computed without dayjs, so the test holds in any
// time zone.
const utcHour = (year: number, month: number, day: number, hour: number) => {
  const date = new Date(year, month - 1, day, hour);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getUTCFullYear()}${pad(date.getUTCMonth() + 1)}${pad(
    date.getUTCDate()
  )}${pad(date.getUTCHours())}`;
};

describe('toUtcDateHour', () => {
  it('converts the hours of a local day to the UTC hours of the partitions', () => {
    expect(toUtcDateHour('20261014', 0, 'YYYYMMDD')).toBe(utcHour(2026, 10, 14, 0));
    expect(toUtcDateHour('20261014', 23, 'YYYYMMDD')).toBe(
      utcHour(2026, 10, 14, 23)
    );
  });

  it('returns nothing for an invalid date', () => {
    expect(toUtcDateHour('2026-10-14', 0, 'YYYYMMDD')).toBeUndefined();
  });
});
