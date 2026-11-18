import { describe, expect, it } from 'vitest';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import remarkMath from 'remark-math';
import {
  endsInsideMath,
  isInlineImageSource,
  normalizeMathDelimiters,
} from '../MarkdownUtils';

const MATH = '$$';

type Node = { type: string; value?: string; children?: Node[] };

/** The tree that ChatMessageMarkdown renders, from its remark plugins. */
const parse = (markdown: string): Node =>
  unified()
    .use(remarkParse)
    .use(remarkGfm)
    .use(remarkBreaks)
    .use(remarkMath, { singleDollarTextMath: false })
    .parse(normalizeMathDelimiters(markdown)) as Node;

/** The node types and values in document order, for structural checks. */
const flatten = (node: Node): string[] => [
  node.value === undefined ? node.type : `${node.type}:${node.value}`,
  ...(node.children ?? []).flatMap(flatten),
];

const mathOf = (markdown: string): string[] =>
  flatten(parse(markdown)).filter((entry) => entry.startsWith('inlineMath:'));

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
  it('renders LaTeX delimiters as math', () => {
    expect(mathOf('Area \\(\\pi r^2\\) here')).toEqual(['inlineMath:\\pi r^2']);
    expect(mathOf('\\[ E = mc^2 \\]')).toEqual([
      'inlineMath:\\displaystyle E = mc^2',
    ]);
  });

  it.each([
    ['closing on a content line', 'See\n\\[\nx\n+ y \\]\n\nNext **bold**'],
    [
      'content on the opening line',
      '\\[ \\begin{aligned} a &= b \\\\\n c &= d \\end{aligned} \\]\n\nNext **bold**',
    ],
    [
      'opening at the end of a line',
      'where \\[\nx = 1\n\\]\nand\n\nNext **bold**',
    ],
  ])('never takes the text after the formula (%s)', (_, markdown) => {
    const tree = flatten(parse(markdown));
    expect(tree).not.toContain('math');
    expect(tree).toContain('text:bold');
    expect(
      tree.filter((entry) => entry.startsWith('inlineMath:'))
    ).toHaveLength(1);
  });

  it('keeps the structure of lists, quotes and tables', () => {
    const list = flatten(
      parse('1. Step:\n   \\[\n   a^2\n   \\]\n   done\n2. next')
    );
    expect(list.filter((entry) => entry === 'listItem')).toHaveLength(2);
    expect(list).toContain('inlineMath:\\displaystyle a^2');
    expect(list).toContain('text:next');

    const quote = flatten(parse('> a\n> \\[\n> x\n> \\]\n> b'));
    expect(quote.filter((entry) => entry === 'blockquote')).toHaveLength(1);
    expect(quote).toContain('inlineMath:\\displaystyle x');

    const table = flatten(parse('| a |\n| - |\n| \\[y\\] |'));
    expect(table).toContain('table');
    expect(table).toContain('inlineMath:\\displaystyle y');
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
