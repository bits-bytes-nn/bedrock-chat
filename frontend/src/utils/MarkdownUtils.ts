/** Images embedded in the message itself, which load nothing from other servers. */
export const isInlineImageSource = (src?: string): src is string =>
  !!src && /^(data|blob):/i.test(src);

const MATH = '$$';
// Fenced code blocks and inline code, which keep their text as it is.
const CODE = '```[\\s\\S]*?(?:```|$)|~~~[\\s\\S]*?(?:~~~|$)|`[^`\\n]*`';
// Existing math, whose LaTeX keeps its brackets.
const EXISTING_MATH = '\\$\\$[\\s\\S]*?(?:\\$\\$|$)';

/** Splits the text so that the matched parts are at the odd indexes. */
const splitOut = (markdown: string, pattern: string): string[] =>
  markdown.split(new RegExp(`(${pattern})`));

/**
 * Turns the LaTeX delimiters `\(…\)` and `\[…\]`, which models often write, into
 * the `$$` math of remark-math, outside of code. Only the delimiters change, so
 * that math inside lists, quotes and tables keeps their structure: on lines of
 * their own they make a math block, within a line inline math. A single `$` is
 * not math, so that prices stay text.
 */
export const normalizeMathDelimiters = (markdown: string): string =>
  splitOut(markdown, `${CODE}|${EXISTING_MATH}`)
    .map((part, index) =>
      index % 2 === 1
        ? part
        : part
            .replace(
              /\\\[([\s\S]+?)\\\]/g,
              (_, math: string) => MATH + math + MATH
            )
            .replace(/\\\((.+?)\\\)/g, (_, math: string) => MATH + math + MATH)
    )
    .join('');

/** Whether the text ends inside `$$` math, where a streaming cursor would break it. */
export const endsInsideMath = (markdown: string): boolean =>
  splitOut(markdown, CODE)
    .filter((_, index) => index % 2 === 0)
    .join('')
    .split(MATH).length %
    2 ===
  0;
