import { describe, expect, it } from 'vitest';
import {
  endsInsideMath,
  isInlineImageSource,
  normalizeMathDelimiters,
} from '../MarkdownUtils';

const MATH = '$$';

describe('isInlineImageSource', () => {
  it('accepts embedded images', () => {
    expect(isInlineImageSource('data:image/png;base64,AAAA')).toBe(true);
    expect(isInlineImageSource('blob:https://example.com/1')).toBe(true);
  });

  it('rejects remote images', () => {
    expect(isInlineImageSource('https://evil.example/p.png?d=secret')).toBe(
      false
    );
    expect(isInlineImageSource('//evil.example/p.png')).toBe(false);
    expect(isInlineImageSource(undefined)).toBe(false);
  });
});

describe('normalizeMathDelimiters', () => {
  it('turns LaTeX delimiters into remark-math math', () => {
    expect(normalizeMathDelimiters('Area \\(\\pi r^2\\) here')).toBe(
      `Area ${MATH}\\pi r^2${MATH} here`
    );
    expect(normalizeMathDelimiters('See\n\\[\nx^2\n\\]\nend')).toBe(
      `See\n${MATH}\nx^2\n${MATH}\nend`
    );
  });

  it('keeps the structure of lists, quotes and tables', () => {
    // Only the delimiters change, with the indentation and prefixes around them.
    expect(
      normalizeMathDelimiters(
        '1. Step:\n   \\[\n   a^2\n   \\]\n   done\n2. next'
      )
    ).toBe(`1. Step:\n   ${MATH}\n   a^2\n   ${MATH}\n   done\n2. next`);
    expect(normalizeMathDelimiters('> a\n> \\[x\\]\n> b')).toBe(
      `> a\n> ${MATH}x${MATH}\n> b`
    );
    expect(normalizeMathDelimiters('| \\[y\\] |')).toBe(`| ${MATH}y${MATH} |`);
  });

  it('leaves code, existing math and single dollars alone', () => {
    const text = 'Costs $5 and $6. `\\(a\\)`\n```\n\\[b\\]\n```';
    expect(normalizeMathDelimiters(text)).toBe(text);
    const math = `${MATH}\\left\\[ x \\right\\]${MATH}`;
    expect(normalizeMathDelimiters(math)).toBe(math);
  });
});

describe('endsInsideMath', () => {
  it('is true only inside unclosed math', () => {
    expect(endsInsideMath(`a ${MATH}x`)).toBe(true);
    expect(endsInsideMath(`a ${MATH}x${MATH} b`)).toBe(false);
    expect(endsInsideMath('```\n' + MATH + '\n```')).toBe(false);
    expect(endsInsideMath('$5')).toBe(false);
  });
});
