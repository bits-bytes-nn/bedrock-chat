/** Images embedded in the message itself, which load nothing from other servers. */
export const isInlineImageSource = (src?: string): src is string =>
  !!src && /^(data|blob):/i.test(src);

// Fenced code blocks and inline code, which keep their text as it is.
const CODE = /(```[\s\S]*?(?:```|$)|~~~[\s\S]*?(?:~~~|$)|`[^`\n]*`)/;
const MATH = '$$';

/** The parts of the text outside of code, at the even indexes of the split. */
const splitCode = (markdown: string): string[] => markdown.split(CODE);

/**
 * Turns the LaTeX delimiters `\(…\)` and `\[…\]`, which models often write, into
 * the `$$` math of remark-math, outside of code. A single `$` is not math, so that
 * prices stay text.
 */
export const normalizeMathDelimiters = (markdown: string): string =>
  splitCode(markdown)
    .map((part, index) =>
      index % 2 === 1
        ? part
        : part
            .replace(
              /\\\[([\s\S]+?)\\\]/g,
              (_, math: string) => `\n${MATH}\n${math.trim()}\n${MATH}\n`
            )
            .replace(/\\\((.+?)\\\)/g, (_, math: string) => MATH + math + MATH)
    )
    .join('');

/** Whether the text ends inside `$$` math, where a streaming cursor would break it. */
export const endsInsideMath = (markdown: string): boolean =>
  splitCode(markdown)
    .filter((_, index) => index % 2 === 0)
    .join('')
    .split(MATH).length %
    2 ===
  0;
