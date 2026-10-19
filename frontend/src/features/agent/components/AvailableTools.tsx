import { Trans, useTranslation } from 'react-i18next';
import {
  AgentTool,
  BedrockAgentConfig,
  BedrockAgentTool,
  InternetAgentTool,
  SearchApiConfig,
  SearchEngine,
  ToolType,
} from '../types';
import { isInternetTool, isBedrockAgentTool } from '../utils/typeGuards';
import Toggle from '../../../components/Toggle';
import { Dispatch, useCallback } from 'react';
import { formatDescription } from '../functions/formatDescription';
import Help from '../../../components/Help';
import Skeleton from '../../../components/Skeleton';
import { TooltipDirection } from '../../../constants';
import { SearchApiConfig as SearchApiConfigComponent } from './SearchApiConfig';
import { BedrockAgentConfig as BedrockAgentConfigComponent } from './BedrockAgentConfig';
import ExpandableDrawerGroup from '../../../components/ExpandableDrawerGroup';
import RadioButton from '../../../components/RadioButton';
import useLoginUser from '../../../hooks/useLoginUser';
import {
  DEFAULT_SEARCH_API_CONFIG,
  SEARCH_API_MAX_RESULTS,
} from '../constants';

const SEARCH_ENGINES: SearchEngine[] = [
  'duckduckgo',
  'firecrawl',
  'tavily',
  'brave',
];

type Props = {
  availableTools: AgentTool[] | undefined;
  tools: AgentTool[];
  setTools: Dispatch<React.SetStateAction<AgentTool[]>>;
  /** Validation errors keyed as `tools-<index>-<field>`. */
  errorMessages?: { [key: string]: string };
};

export const AvailableTools = ({
  availableTools,
  tools,
  setTools,
  errorMessages,
}: Props) => {
  const { t } = useTranslation();
  // Bedrock agents run with the application's role, so only admins can add them.
  const { isAdmin } = useLoginUser();

  const handleChangeTool = useCallback(
    (tool: AgentTool) => () => {
      if (tool.name === 'internet_search') {
        setTools((preTools) => {
          const isEnabled = preTools
            ?.map(({ name }) => name)
            .includes(tool.name);

          const newTools = isEnabled
            ? [...preTools.filter(({ name }) => name != tool.name)]
            : [
                ...preTools,
                {
                  ...tool,
                  toolType: 'internet' as ToolType,
                  searchEngine: 'duckduckgo',
                } as AgentTool,
              ];

          return newTools;
        });
      } else if (tool.name === 'bedrock_agent') {
        setTools((preTools) => {
          const isEnabled = preTools
            ?.map(({ name }) => name)
            .includes(tool.name);

          const newTools = isEnabled
            ? [...preTools.filter(({ name }) => name != tool.name)]
            : [
                ...preTools,
                {
                  ...tool,
                  toolType: 'bedrock_agent' as ToolType,
                  name: 'bedrock_agent',
                  bedrockAgentConfig: {
                    agentId: '',
                    aliasId: '',
                  },
                } as AgentTool,
              ];

          return newTools;
        });
      } else {
        setTools((preTools) =>
          preTools?.map(({ name }) => name).includes(tool.name)
            ? [...preTools.filter(({ name }) => name != tool.name)]
            : [...preTools, tool]
        );
      }
    },
    [setTools]
  );

  const handleSearchApiConfigChange = useCallback(
    (config: SearchApiConfig) => {
      setTools((prevTools) =>
        prevTools.map((tool) => {
          if (tool.name === 'internet_search') {
            return { ...tool, searchApiConfig: config };
          }
          return tool;
        })
      );
    },
    [setTools]
  );

  const handleBedrockAgentConfigChange = useCallback(
    (config: BedrockAgentConfig) => {
      setTools((prevTools) =>
        prevTools.map((tool) => {
          if (tool.name === 'bedrock_agent') {
            return {
              ...tool,
              toolType: 'bedrock_agent' as ToolType,
              name: 'bedrock_agent',
              bedrockAgentConfig: config,
            } as AgentTool;
          }
          return tool;
        })
      );
    },
    [setTools]
  );

  const handleSearchEngineChange = useCallback(
    (value: string) => {
      setTools((prevTools) =>
        prevTools.map((tool) =>
          tool.name === 'internet_search'
            ? {
                ...tool,
                searchEngine: value as SearchEngine,
                // Each engine has its own API key.
                searchApiConfig: undefined,
              }
            : tool
        )
      );
    },
    [setTools]
  );

  const internetSearchToolIndex = tools.findIndex(
    (tool) => tool.name === 'internet_search'
  );
  const internetSearchTool = tools.find(
    (tool): tool is InternetAgentTool =>
      tool.name === 'internet_search' && isInternetTool(tool)
  );
  const searchEngine = internetSearchTool?.searchEngine ?? 'duckduckgo';
  const maxResults = SEARCH_API_MAX_RESULTS[searchEngine];
  const apiKeyError =
    errorMessages?.[`tools-${internetSearchToolIndex}-searchApiConfig.apiKey`];

  return (
    <>
      <div className="flex items-center gap-1">
        <div className="text-lg font-bold dark:text-aws-font-color-dark">
          {t('agent.label')}
        </div>
        <Help direction={TooltipDirection.RIGHT} message={t('agent.hint')} />
      </div>

      <div className="text-sm text-aws-font-color-light/70 dark:text-aws-font-color-dark">
        <Trans
          i18nKey="agent.help.overview"
          components={{
            Link: (
              <a
                href="https://docs.aws.amazon.com/bedrock/latest/userguide/conversation-inference-supported-models-features.html"
                target="_blank"
                rel="noopener noreferrer"
                className="text-aws-sea-blue-light underline dark:text-aws-link-dark"
              />
            ),
          }}
        />
      </div>
      {availableTools === undefined && <Skeleton className="h-12 w-full" />}

      {availableTools?.map((tool) => (
        <div key={tool.name}>
          <div className="flex items-center">
            <Toggle
              ariaLabel={formatDescription(tool, t)}
              value={!!tools?.map(({ name }) => name).includes(tool.name)}
              disabled={
                tool.name === 'bedrock_agent' &&
                !isAdmin &&
                !tools?.some(({ name }) => name === 'bedrock_agent')
              }
              onChange={handleChangeTool(tool)}
            />
            <div className="whitespace-pre-wrap text-sm text-aws-font-color-light/70 dark:text-aws-font-color-dark">
              {formatDescription(tool, t)}
              {tool.name === 'bedrock_agent' && !isAdmin && (
                <div>{t('bot.help.adminOnly')}</div>
              )}
            </div>
          </div>
          {tool.name === 'internet_search' &&
            tools?.map(({ name }) => name).includes('internet_search') && (
              <ExpandableDrawerGroup
                className="ml-8 mt-2"
                isDefaultShow={false}
                // The missing API key is inside, so open it to show the error.
                isForcedShow={!!apiKeyError}
                label={t('agent.tools.internet_search.settings')}>
                <div className="space-y-4">
                  <div
                    role="radiogroup"
                    aria-label={t('agent.tools.internet_search.settings')}>
                    {SEARCH_ENGINES.map((engine) => (
                      <RadioButton
                        key={engine}
                        name="searchEngine"
                        value={engine}
                        checked={searchEngine === engine}
                        label={t(
                          `agent.tools.internet_search.engines.${engine}.label`
                        )}
                        hint={t(
                          `agent.tools.internet_search.engines.${engine}.hint`
                        )}
                        onChange={handleSearchEngineChange}
                      />
                    ))}
                  </div>
                  {maxResults && (
                    <div className="ml-8 text-sm">
                      <SearchApiConfigComponent
                        config={
                          internetSearchTool?.searchApiConfig ??
                          DEFAULT_SEARCH_API_CONFIG
                        }
                        maxResults={maxResults}
                        errorMessage={apiKeyError}
                        onChange={handleSearchApiConfigChange}
                      />
                    </div>
                  )}
                </div>
              </ExpandableDrawerGroup>
            )}
          {tool.name === 'bedrock_agent' &&
            tools?.map(({ name }) => name).includes('bedrock_agent') && (
              <div className="space-y-4">
                <div className="ml-6 text-sm">
                  <BedrockAgentConfigComponent
                    config={
                      tools.find(
                        (t): t is BedrockAgentTool =>
                          t.name === 'bedrock_agent' && isBedrockAgentTool(t)
                      )?.bedrockAgentConfig || {
                        agentId: '',
                        aliasId: '',
                      }
                    }
                    onChange={handleBedrockAgentConfigChange}
                  />
                </div>
              </div>
            )}
        </div>
      ))}
    </>
  );
};
