import { useTranslation } from 'react-i18next';
import { useCallback, useState } from 'react';
import { PiEyeLight, PiEyeSlashLight } from 'react-icons/pi';
import InputText from '../../../components/InputText';
import { Slider } from '../../../components/Slider';
import { SearchApiConfig as SearchApiConfigType } from '../types';

type Props = {
  config: SearchApiConfigType;
  maxResults: number;
  errorMessage?: string;
  onChange: (config: SearchApiConfigType) => void;
};

export const SearchApiConfig = ({
  config,
  maxResults,
  errorMessage,
  onChange,
}: Props) => {
  const { t } = useTranslation();
  const [showPassword, setShowPassword] = useState(false);

  const handleApiKeyChange = useCallback(
    (apiKey: string) => {
      onChange({
        ...config,
        apiKey,
      });
    },
    [config, onChange]
  );

  const handleMaxResultsChange = useCallback(
    (maxResults: number) => {
      onChange({
        ...config,
        maxResults,
      });
    },
    [config, onChange]
  );

  return (
    <div className="space-y-4">
      <div className="flex items-end gap-2">
        <InputText
          className="flex-1"
          label={t('agent.tools.searchApi.apiKey')}
          type={showPassword ? 'text' : 'password'}
          value={config.apiKey || ''}
          errorMessage={errorMessage}
          onChange={handleApiKeyChange}
        />
        <button
          type="button"
          className="size-9 rounded border border-aws-font-color-light/50 p-2 text-sm dark:border-aws-font-color-dark/50"
          aria-label={t('agent.tools.searchApi.showApiKey')}
          aria-pressed={showPassword}
          onClick={() => setShowPassword(!showPassword)}>
          {showPassword ? (
            <PiEyeLight className="size-5" />
          ) : (
            <PiEyeSlashLight className="size-5" />
          )}
        </button>
      </div>
      <Slider
        label={t('agent.tools.searchApi.maxResults')}
        value={config.maxResults}
        onChange={handleMaxResultsChange}
        range={{
          min: 1,
          max: maxResults,
          step: 1,
        }}
      />
    </div>
  );
};
