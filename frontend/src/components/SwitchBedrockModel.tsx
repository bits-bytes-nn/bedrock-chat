import { BaseProps } from '../@types/common';
import useModel from '../hooks/useModel';
import { Listbox, Transition } from '@headlessui/react';
import { Fragment } from 'react/jsx-runtime';
import { useMemo, useEffect } from 'react';
import { PiCaretDown, PiCheck } from 'react-icons/pi';
import { ActiveModels } from '../@types/bot';
import { toCamelCase } from '../utils/StringUtils';
import { ModelItem } from '../@types/global-config';
import { getModelProvider } from '../utils/ModelUtils';

interface Props extends BaseProps {
  activeModels: ActiveModels;
  botId?: string | null;
}

const SwitchBedrockModel: React.FC<Props> = (props) => {
  const {
    availableModels: allModels,
    modelId,
    setModelId,
    getDefaultModel,
  } = useModel(props.botId, props.activeModels);

  const availableModels = useMemo(() => {
    return allModels.filter((model) => {
      if (props.activeModels) {
        return (
          props.activeModels[
            toCamelCase(model.modelId) as keyof ActiveModels
          ] === true
        );
      }
      return true;
    });
  }, [allModels, props.activeModels]);

  // Automatically switch to the default model if the current model is not available
  useEffect(() => {
    const isCurrentModelAvailable = availableModels.some(
      (model) => model.modelId === modelId
    );

    if (!isCurrentModelAvailable && availableModels.length > 0) {
      const defaultModelId = getDefaultModel();
      if (defaultModelId && defaultModelId !== modelId) {
        setModelId(defaultModelId);
      }
    }
  }, [availableModels, modelId, setModelId, getDefaultModel]);

  const modelName = useMemo(() => {
    const foundModel = availableModels.find(
      (model) => model.modelId === modelId
    );
    if (foundModel) {
      return foundModel.label;
    }
    // Only call getDefaultModel if current model is not found
    const defaultModelId = getDefaultModel();
    if (defaultModelId) {
      const defaultModel = availableModels.find(
        (model) => model.modelId === defaultModelId
      );
      return defaultModel?.label ?? '';
    }
    return '';
  }, [availableModels, modelId, getDefaultModel]);

  // Show models grouped by provider, in the order they are defined.
  const groupedModels = useMemo(() => {
    const groups = new Map<string, ModelItem[]>();
    availableModels.forEach((model) => {
      const provider = getModelProvider(model.modelId);
      groups.set(provider, [...(groups.get(provider) ?? []), model]);
    });
    return [...groups.entries()];
  }, [availableModels]);

  return (
    <Listbox value={modelId} onChange={setModelId}>
      <div className="relative">
        <Listbox.Button
          className={`${
            props.className ?? ''
          } group inline-flex w-auto whitespace-nowrap rounded border-aws-squid-ink-light/50 bg-aws-paper-light p-2 px-3 text-base hover:brightness-75 focus-visible:ring-2 focus-visible:ring-aws-sea-blue-light dark:border-aws-squid-ink-dark/50 dark:bg-aws-paper-dark`}>
          <div className="flex items-center justify-between text-xl font-bold text-dark-gray dark:text-light-gray">
            <span>{modelName}</span>
            <PiCaretDown className="ml-2" />
          </div>
        </Listbox.Button>
        <Transition
          as={Fragment}
          enter="transition ease-out duration-200"
          enterFrom="opacity-0 translate-y-1"
          enterTo="opacity-100 translate-y-0"
          leave="transition ease-in duration-150"
          leaveFrom="opacity-100 translate-y-0"
          leaveTo="opacity-0 translate-y-1">
          <Listbox.Options className="absolute left-0 top-14 z-10 mt-0.5 max-h-96 w-[min(24rem,calc(100vw-2rem))] overflow-y-auto rounded border border-aws-font-color-light/50 bg-white text-sm shadow-lg focus:outline-none dark:border-aws-font-color-dark/50 dark:bg-aws-ui-color-dark">
            {groupedModels.map(([provider, models]) => (
              <div key={provider} role="group" aria-label={provider}>
                <div className="sticky top-0 bg-white px-3 pb-1 pt-2 text-xs font-semibold uppercase tracking-wide text-dark-gray dark:bg-aws-ui-color-dark dark:text-aws-font-color-dark">
                  {provider}
                </div>
                {models.map((model) => (
                  <Listbox.Option
                    key={model.modelId}
                    value={model.modelId}
                    className={({ active }) =>
                      `m-1 flex cursor-pointer rounded p-1 px-2 ${
                        active ? 'bg-light-gray dark:bg-aws-paper-dark' : ''
                      }`
                    }>
                    {({ selected }) => (
                      <>
                        <div className="mr-3 flex flex-col items-center justify-center">
                          <PiCheck
                            className={selected ? '' : 'text-transparent'}
                          />
                        </div>
                        <div>
                          <div className="block text-left font-semibold">
                            <span>{model.label}</span>
                          </div>
                          {model.description && (
                            <div className="block whitespace-normal text-left text-xs text-dark-gray dark:text-aws-font-color-dark">
                              <span>{model.description}</span>
                            </div>
                          )}
                        </div>
                      </>
                    )}
                  </Listbox.Option>
                ))}
              </div>
            ))}
          </Listbox.Options>
        </Transition>
      </div>
    </Listbox>
  );
};

export default SwitchBedrockModel;
