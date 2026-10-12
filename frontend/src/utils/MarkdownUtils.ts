/** Images embedded in the message itself, which load nothing from other servers. */
export const isInlineImageSource = (src?: string): src is string =>
  !!src && /^(data|blob):/i.test(src);
