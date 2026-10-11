import { describe, expect, test } from 'vitest';
import { AVAILABLE_MODEL_KEYS } from '../../constants';
import { getModelProvider } from '../ModelUtils';

describe('getModelProvider', () => {
  test('assigns every available model to a known provider', () => {
    const unknown = AVAILABLE_MODEL_KEYS.filter(
      (model) => getModelProvider(model) === 'Other'
    );
    expect(unknown).toEqual([]);
  });

  test('groups models by provider prefix', () => {
    expect(getModelProvider('claude-v5.5-sonnet')).toBe('Anthropic');
    expect(getModelProvider('gpt-oss-20b')).toBe('OpenAI');
    expect(getModelProvider('amazon-nova-2-lite')).toBe('Amazon');
  });
});
