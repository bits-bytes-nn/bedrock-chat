import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import useModel, { useModelState } from '../useModel';

vi.mock('../useGlobalConfig', () => ({
  default: () => ({ getGlobalConfig: () => ({ data: undefined }) }),
}));

type UseModelResult = ReturnType<typeof useModel>;

/**
 * Render useModel once, without effects, and return what it returned. Server
 * rendering reads the initial store state, so tests read the store directly.
 */
const renderUseModel = (): UseModelResult => {
  let result: UseModelResult | undefined;
  const Probe = () => {
    result = useModel();
    return null;
  };
  renderToStaticMarkup(<Probe />);
  return result!;
};

describe('useModel', () => {
  const storage = new Map<string, string>();

  beforeEach(() => {
    storage.clear();
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => storage.set(key, value),
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test('setModelId saves the model that new chats start with', () => {
    renderUseModel().setModelId('claude-v5-sonnet');

    expect(storage.get('recentUseModelId')).toBe('claude-v5-sonnet');
    expect(useModelState.getState().modelId).toBe('claude-v5-sonnet');
  });

  test('setModelIdWithoutSaving shows a loaded conversation model only', () => {
    storage.set('recentUseModelId', 'claude-v5-sonnet');

    renderUseModel().setModelIdWithoutSaving('amazon-nova-pro');

    expect(useModelState.getState().modelId).toBe('amazon-nova-pro');
    expect(storage.get('recentUseModelId')).toBe('claude-v5-sonnet');
  });
});
