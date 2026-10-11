// Model IDs start with a provider-specific prefix, for example 'claude-v5.5-sonnet'.
const PROVIDER_PREFIXES: [prefix: string, provider: string][] = [
  ['claude-', 'Anthropic'],
  ['gpt-', 'OpenAI'],
  ['amazon-', 'Amazon'],
  ['mistral-', 'Mistral AI'],
  ['deepseek-', 'DeepSeek'],
  ['llama', 'Meta'],
];

export const getModelProvider = (modelId: string): string =>
  PROVIDER_PREFIXES.find(([prefix]) => modelId.startsWith(prefix))?.[1] ??
  'Other';
