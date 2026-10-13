import { create } from 'zustand';
import { Model } from '../@types/conversation';
import { ModelItem } from '../@types/global-config';
import { AVAILABLE_MODEL_KEYS } from '../constants/index';
import { useEffect, useMemo, useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import useLocalStorage from './useLocalStorage';
import useGlobalConfig from './useGlobalConfig';
import { ActiveModels } from '../@types/bot';
import { toCamelCase } from '../utils/StringUtils';

const IMAGE_MEDIA_TYPES = [
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
];

// Selected when no model is available, so that a model ID is always set.
const FALLBACK_MODEL_ID: Model = 'amazon-nova-lite';

// These models return reasoning on every request, so the toggle is always on.
const ALWAYS_REASONING = {
  supportReasoning: true,
  forceReasoningEnabled: true,
};

// Capabilities shown in the UI. The backend keeps the request parameters for each
// model in backend/app/model_registry.py, and a backend test keeps both lists in sync.
// Newest models first within each provider.
const MODELS: Omit<ModelItem, 'label' | 'description'>[] = [
  {
    modelId: 'claude-v5.5-opus',
    supportMediaType: IMAGE_MEDIA_TYPES,
    supportReasoning: true,
  },
  {
    modelId: 'claude-v5.5-sonnet',
    supportMediaType: IMAGE_MEDIA_TYPES,
    supportReasoning: true,
  },
  {
    modelId: 'claude-v5.5-haiku',
    supportMediaType: IMAGE_MEDIA_TYPES,
    supportReasoning: true,
  },
  {
    modelId: 'claude-v5-opus',
    supportMediaType: IMAGE_MEDIA_TYPES,
    supportReasoning: true,
  },
  {
    modelId: 'claude-v5-sonnet',
    supportMediaType: IMAGE_MEDIA_TYPES,
    supportReasoning: true,
  },
  {
    modelId: 'claude-v4.8-opus',
    supportMediaType: IMAGE_MEDIA_TYPES,
    supportReasoning: true,
  },
  {
    modelId: 'claude-v4.7-opus',
    supportMediaType: IMAGE_MEDIA_TYPES,
    supportReasoning: true,
  },
  {
    modelId: 'claude-v4.6-opus',
    supportMediaType: IMAGE_MEDIA_TYPES,
    supportReasoning: true,
  },
  {
    modelId: 'claude-v4.6-sonnet',
    supportMediaType: IMAGE_MEDIA_TYPES,
    supportReasoning: true,
  },
  {
    modelId: 'claude-v4.5-opus',
    supportMediaType: IMAGE_MEDIA_TYPES,
    supportReasoning: true,
  },
  {
    modelId: 'claude-v4.5-sonnet',
    supportMediaType: IMAGE_MEDIA_TYPES,
    supportReasoning: true,
  },
  {
    modelId: 'claude-v4.5-haiku',
    supportMediaType: IMAGE_MEDIA_TYPES,
    supportReasoning: true,
  },
  {
    modelId: 'gpt-6.1-sol',
    supportMediaType: IMAGE_MEDIA_TYPES,
    ...ALWAYS_REASONING,
  },
  {
    modelId: 'gpt-6-astra',
    supportMediaType: IMAGE_MEDIA_TYPES,
    ...ALWAYS_REASONING,
  },
  {
    modelId: 'gpt-6-sol',
    supportMediaType: IMAGE_MEDIA_TYPES,
    ...ALWAYS_REASONING,
  },
  {
    modelId: 'gpt-6-luna',
    supportMediaType: IMAGE_MEDIA_TYPES,
    ...ALWAYS_REASONING,
  },
  {
    modelId: 'gpt-5.6-terra',
    supportMediaType: IMAGE_MEDIA_TYPES,
    ...ALWAYS_REASONING,
  },
  {
    modelId: 'gpt-5.6-sol',
    supportMediaType: IMAGE_MEDIA_TYPES,
    ...ALWAYS_REASONING,
  },
  {
    modelId: 'gpt-5.6-luna',
    supportMediaType: IMAGE_MEDIA_TYPES,
    ...ALWAYS_REASONING,
  },
  {
    modelId: 'gpt-5.5',
    supportMediaType: IMAGE_MEDIA_TYPES,
    ...ALWAYS_REASONING,
  },
  { modelId: 'gpt-oss-120b', supportMediaType: [], ...ALWAYS_REASONING },
  { modelId: 'gpt-oss-20b', supportMediaType: [], ...ALWAYS_REASONING },
  {
    modelId: 'amazon-nova-2-lite',
    supportMediaType: IMAGE_MEDIA_TYPES,
    supportReasoning: false,
  },
  {
    modelId: 'amazon-nova-pro',
    supportMediaType: IMAGE_MEDIA_TYPES,
    supportReasoning: false,
  },
  {
    modelId: 'amazon-nova-lite',
    supportMediaType: IMAGE_MEDIA_TYPES,
    supportReasoning: false,
  },
  {
    modelId: 'amazon-nova-micro',
    supportMediaType: [],
    supportReasoning: false,
  },
  { modelId: 'mistral-large-2', supportMediaType: [], supportReasoning: false },
  { modelId: 'mistral-large', supportMediaType: [], supportReasoning: false },
  { modelId: 'deepseek-r1', supportMediaType: [], ...ALWAYS_REASONING },
  {
    modelId: 'llama3-3-70b-instruct',
    supportMediaType: [],
    supportReasoning: false,
  },
];

const useModelState = create<{
  modelId: Model | undefined;
  setModelId: (m: Model) => void;
}>((set) => ({
  modelId: undefined, // Will be set by useEffect based on config/localStorage
  setModelId: (m) => {
    set({
      modelId: m,
    });
  },
}));

// Store the Previous BotId
const usePreviousBotId = (botId: string | null | undefined) => {
  const ref = useRef<string | null | undefined>();

  useEffect(() => {
    ref.current = botId;
  }, [botId]);

  return ref.current;
};

const useModel = (botId?: string | null, activeModels?: ActiveModels) => {
  const { getGlobalConfig } = useGlobalConfig();
  const { data: globalConfig } = getGlobalConfig();

  const processedActiveModels = useMemo(() => {
    // Early return if activeModels is provided and not empty
    if (activeModels && Object.keys(activeModels).length > 0) {
      return activeModels;
    }

    // Create a new object with all models set to true
    return AVAILABLE_MODEL_KEYS.reduce((acc: ActiveModels, model: Model) => {
      // Optimize string replacement by doing it in one operation
      acc[toCamelCase(model) as keyof ActiveModels] = true;
      return acc;
    }, {} as ActiveModels);
  }, [activeModels]);

  const { t } = useTranslation();
  const previousBotId = usePreviousBotId(botId);

  const availableModels = useMemo<ModelItem[]>(() => {
    return MODELS.map((model) => ({
      ...model,
      label: t(`model.${model.modelId}.label`),
      description: t(`model.${model.modelId}.description`),
    })).filter((model) => {
      // Filter based on global configuration if available
      if (
        globalConfig?.globalAvailableModels &&
        globalConfig.globalAvailableModels.length > 0
      ) {
        return globalConfig.globalAvailableModels.includes(model.modelId);
      }
      // If no global config, show all models
      return true;
    }) as ModelItem[];
  }, [t, globalConfig]);

  const [filteredModels, setFilteredModels] = useState(availableModels);
  const { modelId, setModelId } = useModelState();
  const [recentUseModelId, setRecentUseModelId] = useLocalStorage(
    'recentUseModelId',
    '' // Will use getDefaultModel() if localStorage is empty
  );

  // Save the model id by each bot
  const [botModelId, setBotModelId] = useLocalStorage(
    botId ? `bot_model_${botId}` : 'temp_model',
    ''
  );

  // Update filtered models when activeModels changes
  useEffect(() => {
    if (processedActiveModels) {
      const filtered = availableModels.filter((model: ModelItem) => {
        const key = toCamelCase(model.modelId) as keyof ActiveModels;
        return processedActiveModels[key] !== false;
      });
      setFilteredModels(filtered);
    }
  }, [processedActiveModels, availableModels]);

  const getDefaultModel = useCallback((): Model => {
    // Use the default model from global config if available
    const configDefaultModel = globalConfig?.defaultModel as Model | undefined;

    if (configDefaultModel) {
      // Check if the configured default model is available
      const defaultModelAvailable = filteredModels.some(
        (m: ModelItem) => m.modelId === configDefaultModel
      );
      if (defaultModelAvailable) {
        return configDefaultModel;
      }
    }

    // If config default is not available or not set yet, select the first model
    return filteredModels[0]?.modelId ?? FALLBACK_MODEL_ID;
  }, [filteredModels, globalConfig?.defaultModel]);

  // select the model via list of activeModels
  const selectModel = useCallback(
    (targetModelId: Model) => {
      const modelExists = filteredModels.some(
        (m: ModelItem) => toCamelCase(m.modelId) === toCamelCase(targetModelId)
      );
      return modelExists ? targetModelId : getDefaultModel();
    },
    [filteredModels, getDefaultModel]
  );

  useEffect(() => {
    if (processedActiveModels === undefined) {
      return;
    }

    // botId is changed
    if (previousBotId !== botId) {
      // BotId is undefined, select recent modelId
      if (!botId) {
        setModelId(selectModel(recentUseModelId as Model));
        return;
      }

      // get botModelId from localStorage
      // When acquired from botModelID, settings for previousBotID are acquired, so a key is specified and acquired directly from local storage.
      const botModelId = localStorage.getItem(`bot_model_${botId}`);

      // modelId is in the the LocalStorage. use the saved modelId.
      if (botModelId) {
        setModelId(selectModel(botModelId as Model));
      } else {
        // If there is no bot-specific model ID, check if the last model used can be used
        const lastModelAvailable = filteredModels.some(
          (m: ModelItem) => m.modelId === recentUseModelId
        );

        // If the last model used is available, use it.
        if (lastModelAvailable) {
          setModelId(selectModel(recentUseModelId as Model));
          return;
        } else {
          // Use the default model if not available
          setModelId(selectModel(getDefaultModel()));
        }
      }
    } else {
      // Processing when botId and previousBotID are the same, but there is an update in FilteredModels
      if (botId) {
        const lastModelAvailable = filteredModels.some(
          (m: ModelItem) =>
            toCamelCase(m.modelId) === toCamelCase(recentUseModelId) ||
            toCamelCase(m.modelId) === toCamelCase(botModelId)
        );
        if (!lastModelAvailable) {
          setModelId(selectModel(getDefaultModel()));
        } else {
          setModelId(selectModel(recentUseModelId as Model));
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [botId]);

  // The global config arrives after the first render, when the first model in the
  // list was selected as a fallback. Apply the configured default unless the user
  // has already chosen a model.
  useEffect(() => {
    if (!botId && !recentUseModelId && globalConfig?.defaultModel) {
      setModelId(selectModel(globalConfig.defaultModel as Model));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [globalConfig?.defaultModel]);

  const model = useMemo(() => {
    if (!modelId) {
      return undefined;
    }
    return filteredModels.find(
      (model: ModelItem) => toCamelCase(model.modelId) === toCamelCase(modelId)
    );
  }, [filteredModels, modelId]);

  return {
    modelId: modelId ?? getDefaultModel(),
    setModelId: (model: Model) => {
      setRecentUseModelId(model);
      if (botId) {
        setBotModelId(model);
      }
      setModelId(model);
    },
    model,
    disabledImageUpload: (model?.supportMediaType.length ?? 0) === 0,
    acceptMediaType:
      model?.supportMediaType.flatMap((mediaType: string) => {
        const ext = mediaType.split('/')[1];
        return ext === 'jpeg' ? ['.jpg', '.jpeg'] : [`.${ext}`];
      }) ?? [],
    availableModels: filteredModels,
    forceReasoningEnabled: model?.forceReasoningEnabled ?? false,
    getDefaultModel,
  };
};

export default useModel;
