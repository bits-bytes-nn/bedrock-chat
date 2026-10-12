import { describe, expect, it, vi } from 'vitest';
import {
  ConversionCanceledError,
  ConversionStatus,
  textToBase64,
  waitForConversion,
} from '../ConversionUtils';

const options = { sleep: vi.fn(async () => {}), intervalMs: 10, timeoutMs: 30 };
const failure = new Error('network');
const status = (
  s: ConversionStatus['status'],
  reason = ''
): ConversionStatus => ({
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

  it('tolerates a transient poll error', async () => {
    const fetchStatus = vi
      .fn()
      .mockRejectedValueOnce(failure)
      .mockResolvedValueOnce(status('COMPLETED'));

    await expect(
      waitForConversion(status('IN_PROGRESS'), fetchStatus, options)
    ).resolves.toEqual(status('COMPLETED'));
  });

  it('stops after repeated poll errors', async () => {
    const fetchStatus = vi.fn().mockRejectedValue(failure);
    await expect(
      waitForConversion(status('IN_PROGRESS'), fetchStatus, {
        ...options,
        timeoutMs: 1000,
      })
    ).rejects.toThrow('network');
    expect(fetchStatus).toHaveBeenCalledTimes(3);
  });

  it('stops when aborted', async () => {
    const controller = new AbortController();
    controller.abort();
    await expect(
      waitForConversion(status('IN_PROGRESS'), vi.fn(), {
        ...options,
        signal: controller.signal,
      })
    ).rejects.toBeInstanceOf(ConversionCanceledError);
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
