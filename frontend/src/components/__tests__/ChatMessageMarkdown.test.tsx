import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import ChatMessageMarkdown from '../ChatMessageMarkdown';

const render = (text: string) =>
  renderToStaticMarkup(
    <ChatMessageMarkdown messageId="m" isStreaming>
      {text}
    </ChatMessageMarkdown>
  );

describe('ChatMessageMarkdown images', () => {
  it('shows remote images as links instead of loading them', () => {
    const html = render('![logo](https://example.com/p.png?d=secret)');
    expect(html).not.toContain('<img');
    expect(html).toContain('href="https://example.com/p.png?d=secret"');
    expect(html).toContain('>logo</a>');
  });

  it('shows only the text of images whose source was removed', () => {
    // react-markdown drops data: URLs by default.
    const html = render('![dot](data:image/png;base64,AAAA)');
    expect(html).not.toContain('<img');
    expect(html).not.toContain('href=""');
    expect(html).toContain('dot');
  });
});
