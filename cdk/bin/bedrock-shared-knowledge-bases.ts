import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { BedrockSharedKnowledgeBasesStack } from "../lib/bedrock-shared-knowledge-bases-stack";
import {
  getEmbeddingModel,
  getChunkingStrategy,
  getChunkingOptions,
  getAnalyzer,
  getParsingModel,
} from "../lib/utils/bedrock-knowledge-base-args";
import {
  BedrockFoundationModel,
  IInvokable,
} from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/bedrock";
import { ChunkingStrategy } from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/bedrock/data-sources/chunking";
import { Analyzer } from "@cdklabs/generative-ai-cdk-constructs/lib/cdk-lib/opensearch-vectorindex";
import { resolveBedrockSharedKnowledgeBasesParameters } from "../lib/utils/parameter-models";

const app = new cdk.App();

// Get parameters specific to Bedrock Custom Bot
const params = resolveBedrockSharedKnowledgeBasesParameters();

// Parse JSON strings into objects
const sharedKnowledgeBasesJson = JSON.parse(params.sharedKnowledgeBases);

// Define interfaces for typed configuration objects
interface BaseConfig {
  envName: string;
  envPrefix: string;
  bedrockRegion: string;
  documentBucketName: string;
  enableRagReplicas: boolean;
}

interface KnowledgeConfig {
  knowledgeBaseHash: string;
  embeddingsModel: BedrockFoundationModel;
  parsingModel: IInvokable | undefined;
  instruction?: string;
  analyzer?: Analyzer | undefined;
}

interface ChunkingConfig {
  chunkingStrategy: ChunkingStrategy;
  maxTokens?: number;
  overlapPercentage?: number;
  overlapTokens?: number;
  maxParentTokenSize?: number;
  maxChildTokenSize?: number;
  bufferSize?: number;
  breakpointPercentileThreshold?: number;
}

// Extract and organize configuration by category
const baseConfig: BaseConfig = {
  envName: params.envName,
  envPrefix: params.envPrefix,
  bedrockRegion: params.bedrockRegion,
  documentBucketName: params.documentBucketName,
  enableRagReplicas: params.enableRagReplicas === true,
};

const knowledgeBases = sharedKnowledgeBasesJson.map((sharedKnowledgeBase: any) => {
  const knowledgeBaseJson = sharedKnowledgeBase.KnowledgeBase;
  const knowledgeBaseHash = sharedKnowledgeBase.KnowledgeBaseHash;
  const knowledgeConfig: KnowledgeConfig = {
    knowledgeBaseHash: knowledgeBaseHash,
    embeddingsModel: getEmbeddingModel(knowledgeBaseJson.embeddings_model),
    parsingModel: getParsingModel(knowledgeBaseJson.parsing_model),
    instruction: knowledgeBaseJson.instruction,
    analyzer: knowledgeBaseJson.open_search?.analyzer
      ? getAnalyzer(knowledgeBaseJson.open_search.analyzer)
      : undefined,
  };

  // Extract chunking configuration
  const chunkingParams = getChunkingOptions(
    knowledgeBaseJson.chunking_configuration
  );

  const chunkingConfig: ChunkingConfig = {
    ...chunkingParams,
    chunkingStrategy: getChunkingStrategy(
      knowledgeBaseJson.chunking_configuration?.chunking_strategy,
      knowledgeBaseJson.embeddings_model,
      chunkingParams
    ),
  };

  // Log organized configurations for debugging
  console.log("Base Configuration:", JSON.stringify(baseConfig, null, 2));
  console.log(
    "Knowledge Configuration:",
    JSON.stringify(
      {
        ...knowledgeConfig,
        embeddingsModel: knowledgeConfig.embeddingsModel.toString(),
        parsingModel: knowledgeConfig.parsingModel?.invokableArn,
        analyzer: knowledgeConfig.analyzer ? "configured" : "undefined",
      },
      null,
      2
    )
  );
  console.log(
    "Chunking Configuration:",
    JSON.stringify(
      {
        ...chunkingConfig,
        chunkingStrategy: chunkingConfig.chunkingStrategy.toString(),
      },
      null,
      2
    )
  );
  return {
    knowledgeConfig,
    chunkingConfig,
  };
});

// Create the stack
new BedrockSharedKnowledgeBasesStack(app, "BrChatSharedKbStack", {
  // Environment configuration
  env: {
    region: baseConfig.bedrockRegion,
  },

  // Base configuration
  documentBucketName: baseConfig.documentBucketName,
  enableRagReplicas: baseConfig.enableRagReplicas,

  knowledgeBases: knowledgeBases.map((knowledgeBase: any) => ({
    // Knowledge base configuration
    knowledgeBaseHash: knowledgeBase.knowledgeConfig.knowledgeBaseHash,
    embeddingsModel: knowledgeBase.knowledgeConfig.embeddingsModel,
    parsingModel: knowledgeBase.knowledgeConfig.parsingModel,
    instruction: knowledgeBase.knowledgeConfig.instruction,
    analyzer: knowledgeBase.knowledgeConfig.analyzer,

    // Chunking configuration
    chunkingStrategy: knowledgeBase.chunkingConfig.chunkingStrategy,
  })),
});

cdk.Tags.of(app).add("CDKEnvironment", baseConfig.envName);
