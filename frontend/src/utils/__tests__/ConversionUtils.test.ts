import { describe, expect, it, vi } from 'vitest';
import {
  ConversionStatus,
  textToBase64,
  waitForConversion,
} from '../ConversionUtils';

const options = { sleep: vi.fn(async () => {}), intervalMs: 10, timeoutMs: 30 };
const status = (s: ConversionStatus['status'], reason = ''): ConversionStatus => ({
  status: s,
  reason,
});

describe('waitForConversion', () => {
  it('polls until the conversion completes', async () => {
    const fetchStatus = vi
      .fn()
      .mockResolvedValueOnce(status('IN_PROGRESS'))
      .mockResolvedValueOnce(status('COMPLETED'));

    await expect(
      waitForConversion(status('IN_PROGRESS'), fetchStatus, options)
    ).resolves.toEqual(status('COMPLETED'));
    expect(fetchStatus).toHaveBeenCalledTimes(2);
  });

  it('throws the failure reason', async () => {
    await expect(
      waitForConversion(status('FAILED', 'Unsupported media'), vi.fn(), options)
    ).rejects.toThrow('Unsupported media');
  });

  it('gives up after the timeout', async () => {
    const fetchStatus = vi.fn().mockResolvedValue(status('IN_PROGRESS'));
    await expect(
      waitForConversion(status('IN_PROGRESS'), fetchStatus, options)
    ).rejects.toThrow('timed out');
  });
});

describe('textToBase64', () => {
  it('encodes UTF-8 text', () => {
    expect(atob(textToBase64('회의'))).toBe(
      String.fromCharCode(...new TextEncoder().encode('회의'))
    );
  });
});
