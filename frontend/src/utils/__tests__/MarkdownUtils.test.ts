import { describe, expect, it } from 'vitest';
import { isInlineImageSource } from '../MarkdownUtils';

describe('isInlineImageSource', () => {
  it('accepts embedded images', () => {
    expect(isInlineImageSource('data:image/png;base64,AAAA')).toBe(true);
    expect(isInlineImageSource('blob:https://example.com/1')).toBe(true);
  });

  it('rejects remote images', () => {
    expect(isInlineImageSource('https://evil.example/p.png?d=secret')).toBe(false);
    expect(isInlineImageSource('//evil.example/p.png')).toBe(false);
    expect(isInlineImageSource(undefined)).toBe(false);
  });
});
