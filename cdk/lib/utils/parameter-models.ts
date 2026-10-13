import { z } from "zod";
import { TIdentityProvider } from "./identity-provider";
import { App } from "aws-cdk-lib";

export const BotStoreLanguageSchema = z.enum([
  "en",
  "de",
  "fr",
  "es",
  "ja",
  "ko",
  "zhhans",
  "zhhant",
  "it",
  "nb",
  "th",
  "id",
  "ms",
]);

/**
 * Base parameters schema that is common across all entry points
 */
const BaseParametersSchema = z.object({
  // CDK Environments
  envName: z
    .string()
    .max(10)
    .regex(/^$|^[a-zA-Z][a-zA-Z0-9]*$/)
    .default("default"),
  envPrefix: z.string().default(""),

  // Bedrock configuration
  bedrockRegion: z.string().default("us-east-1"),
  enableBedrockGlobalInference: z.boolean().default(true),
  enableBedrockCrossRegionInference: z.boolean().default(true),
});

/**
 * Helper function to get environment variables with fallback
 * @param name Environment variable name
 * @param defaultValue Default value if environment variable is not set
 * @returns The environment variable value or default value
 */
function getEnvVar(name: string, defaultValue?: string): string | undefined {
  const value = process.env[name];
  return value !== undefined ? value : defaultValue;
}

function getBooleanEnvVar(name: string): boolean | undefined {
  const value = getEnvVar(name);
  return value === undefined ? undefined : value === "true";
}

/**
 * Parameters schema for the main Bedrock Chat application
 */
const BedrockChatParametersSchema = BaseParametersSchema.extend({

  // Frontend WAF toggle (CloudFront scope)
  // Set to 'false' if you're unable to deploy resources in us-east-1
  enableFrontendWaf: z.boolean().default(true),

  // Frontend (CloudFront) IPv6 toggle
  enableFrontendIpv6: z.boolean().default(true),

  // IP address restrictions - enforced by WAF if enabled
  allowedIpV4AddressRanges: z
    .array(z.string())
    .default(["0.0.0.0/1", "128.0.0.0/1"]),
  allowedIpV6AddressRanges: z
    .array(z.string())
    .default([
      "0000:0000:0000:0000:0000:0000:0000:0000/1",
      "8000:0000:0000:0000:0000:0000:0000:0000/1",
    ]),
  publishedApiAllowedIpV4AddressRanges: z
    .array(z.string())
    .default(["0.0.0.0/1", "128.0.0.0/1"]),
  publishedApiAllowedIpV6AddressRanges: z
    .array(z.string())
    .default([
      "0000:0000:0000:0000:0000:0000:0000:0000/1",
      "8000:0000:0000:0000:0000:0000:0000:0000/1",
    ]),

  // Optional list of allowed countries specified as ISO 3166-1 alpha-2 codes
  allowedCountries: z.array(z.string()).default([]),

  // Authentication and user management
  identityProviders: z
    .unknown()
    .transform((val) =>
      Array.isArray(val) ? (val as TIdentityProvider[]) : []
    )
    .pipe(z.array(z.custom<TIdentityProvider>()))
    .default([]),
  userPoolDomainPrefix: z.string().default(""),
  allowedSignUpEmailDomains: z.array(z.string()).default([]),
  // Off by default: members of CreatingBotAllowed can create knowledge bases, each
  // with its own OpenSearch Serverless collection.
  autoJoinUserGroups: z.array(z.string()).default([]),
  // Off by default: users are created by an administrator.
  selfSignUpEnabled: z.boolean().default(false),

  // Performance and availability
  enableRagReplicas: z.boolean().default(true),
  enableLambdaSnapStart: z.boolean().default(true),

  // Custom domain configuration
  alternateDomainName: z.string().default(""),
  hostedZoneId: z.string().default(""),

  // BotStore
  enableBotStore: z.boolean().default(true),
  enableBotStoreReplicas: z.boolean().default(false),
  botStoreLanguage: BotStoreLanguageSchema.default("en"),

  // ID token refresh interval
  tokenValidMinutes: z.number().default(30),

  // Global model configuration
  // If not configured (empty array), all models are available
  globalAvailableModels: z.array(z.string()).default([]),

  // Default model to be selected when user first visits the app
  defaultModel: z.string().optional(),

  // Model used for generating conversation titles
  // (defaults to defaultModel, then a hardcoded default in get_title_model())
  titleModel: z.string().optional(),

  // Frontend branding
  logoPath: z.string().default(""),

  // Operations
  // Email address subscribed to alarm notifications. Leave empty to only create the topic.
  alarmEmail: z.string().default(""),
  // Alarm when the chat answers of a day cost more than this, in USD (0 turns it off).
  // Computed with the model prices in the backend, including published APIs.
  dailyChatCostAlarmUsd: z.number().min(0).default(100),
  // Bots with their own knowledge base per user; each has an OpenSearch Serverless
  // collection billed while it exists. 0 means no limit. Admins are not limited.
  maxDedicatedKnowledgeBasesPerUser: z.number().int().min(0).default(2),
  // Days to keep the hourly conversation exports for usage analysis. They contain
  // conversation text, including deleted conversations.
  usageAnalysisRetentionDays: z.number().int().min(1).default(90),
  // Requests per second for the REST and WebSocket APIs. API Gateway's account limit
  // still applies; these defaults only stop runaway clients.
  apiThrottleRateLimit: z.number().default(500),
  apiThrottleBurstLimit: z.number().default(1000),

  // debug parameter
  devAccessIamRoleArn: z.string().default("")
});

/**
 * Parameters schema for API publishing
 */
const ApiPublishParametersSchema = BaseParametersSchema.extend({
  // API publishing configuration
  publishedApiThrottleRateLimit: z
    .string()
    .optional()
    .transform((val) => (val ? Number(val) : undefined)),
  publishedApiThrottleBurstLimit: z
    .string()
    .optional()
    .transform((val) => (val ? Number(val) : undefined)),
  publishedApiQuotaLimit: z
    .string()
    .optional()
    .transform((val) => (val ? Number(val) : undefined)),
  publishedApiQuotaPeriod: z.enum(["DAY", "WEEK", "MONTH"]).optional(),
  publishedApiDeploymentStage: z.string().default("api"),
  publishedApiId: z.string().optional(),
  publishedApiAllowedOrigins: z.string().default('["*"]'),
  // Model settings of the main API, passed through as-is.
  globalAvailableModels: z.string().default("[]"),
  defaultModel: z.string().default(""),
  titleModel: z.string().default(""),
});

/**
 * Parameters schema for Bedrock Custom Bot
 */
const BedrockCustomBotParametersSchema = BaseParametersSchema.extend({
  // Bot configuration
  ownerUserId: z.string(),
  botId: z.string(),
  documentBucketName: z.string(),
  knowledge: z.string(),
  knowledgeBase: z.string(),
  guardrails: z.string(),
  enableRagReplicas: z
    .string()
    .optional()
    .transform((val) => val === "true")
    .default("false"),
});

/**
 * Parameters schema for shared Knowledge Bases
 */
const BedrockSharedKnowledgeBasesParametersSchema = BaseParametersSchema.extend({
  // Knowledge Base configuration
  sharedKnowledgeBases: z.string(),
  documentBucketName: z.string(),
  enableRagReplicas: z
    .string()
    .optional()
    .transform((val) => val === "true")
    .default("false"),
});

/**
 * Type definitions for each parameter set
 */
// Input types (for user input, default values are optional)
export type BedrockChatParametersInput = z.input<
  typeof BedrockChatParametersSchema
>;

// Output types (for function returns, all properties are required)
export type BedrockChatParameters = z.infer<typeof BedrockChatParametersSchema>;
export type ApiPublishParameters = z.infer<typeof ApiPublishParametersSchema>;
export type BedrockCustomBotParameters = z.infer<
  typeof BedrockCustomBotParametersSchema
>;
export type BedrockSharedKnowledgeBasesParameters = z.infer<
  typeof BedrockSharedKnowledgeBasesParametersSchema
>;

/**
 * Parse and validate parameters for the main Bedrock Chat application.
 * If you omit parametersInput, context parameters and environment variables are used.
 * @param app CDK App instance
 * @param parametersInput (optional) Input parameters that should be used instead of context parameters
 * @returns Validated parameters object
 */
export function resolveBedrockChatParameters(
  app: App,
  parametersInput?: BedrockChatParametersInput
): BedrockChatParameters {
  // If parametersInput is provided, use it directly
  if (parametersInput) {
    return BedrockChatParametersSchema.parse(parametersInput);
  }

  // Get environment variables
  const envName = app.node.tryGetContext("envName") || "default";
  const envPrefix = envName === "default" ? "" : envName;

  // Otherwise, get parameters from context
  const contextParams = {
    envName,
    envPrefix,
    bedrockRegion: app.node.tryGetContext("bedrockRegion"),
    enableFrontendWaf: app.node.tryGetContext("enableFrontendWaf"),
    enableFrontendIpv6: app.node.tryGetContext("enableFrontendIpv6"),
    allowedIpV4AddressRanges: app.node.tryGetContext(
      "allowedIpV4AddressRanges"
    ),
    allowedIpV6AddressRanges: app.node.tryGetContext(
      "allowedIpV6AddressRanges"
    ),
    allowedCountries: app.node.tryGetContext("allowedCountries"),
    identityProviders: app.node.tryGetContext("identityProviders"),
    userPoolDomainPrefix: app.node.tryGetContext("userPoolDomainPrefix"),
    allowedSignUpEmailDomains: app.node.tryGetContext(
      "allowedSignUpEmailDomains"
    ),
    autoJoinUserGroups: app.node.tryGetContext("autoJoinUserGroups"),
    selfSignUpEnabled: app.node.tryGetContext("selfSignUpEnabled"),
    publishedApiAllowedIpV4AddressRanges: app.node.tryGetContext(
      "publishedApiAllowedIpV4AddressRanges"
    ),
    publishedApiAllowedIpV6AddressRanges: app.node.tryGetContext(
      "publishedApiAllowedIpV6AddressRanges"
    ),
    enableRagReplicas: app.node.tryGetContext("enableRagReplicas"),
    enableBedrockGlobalInference: app.node.tryGetContext(
      "enableBedrockGlobalInference"
    ),
    enableBedrockCrossRegionInference: app.node.tryGetContext(
      "enableBedrockCrossRegionInference"
    ),
    enableLambdaSnapStart: app.node.tryGetContext("enableLambdaSnapStart"),
    alternateDomainName: app.node.tryGetContext("alternateDomainName"),
    hostedZoneId: app.node.tryGetContext("hostedZoneId"),
    enableBotStore: app.node.tryGetContext("enableBotStore"),
    enableBotStoreReplicas: app.node.tryGetContext("enableBotStoreReplicas"),
    botStoreLanguage: app.node.tryGetContext("botStoreLanguage"),
    globalAvailableModels: app.node.tryGetContext("globalAvailableModels"),
    defaultModel: app.node.tryGetContext("defaultModel"),
    titleModel: app.node.tryGetContext("titleModel"),
    logoPath: app.node.tryGetContext("logoPath"),
    devAccessIamRoleArn: app.node.tryGetContext("devAccessIamRoleArn"),
    tokenValidMinutes: app.node.tryGetContext("tokenValidMinutes"),
    alarmEmail: app.node.tryGetContext("alarmEmail"),
    dailyChatCostAlarmUsd: app.node.tryGetContext("dailyChatCostAlarmUsd"),
    maxDedicatedKnowledgeBasesPerUser: app.node.tryGetContext(
      "maxDedicatedKnowledgeBasesPerUser"
    ),
    usageAnalysisRetentionDays: app.node.tryGetContext("usageAnalysisRetentionDays"),
    apiThrottleRateLimit: app.node.tryGetContext("apiThrottleRateLimit"),
    apiThrottleBurstLimit: app.node.tryGetContext("apiThrottleBurstLimit"),
  };

  return BedrockChatParametersSchema.parse(contextParams);
}

/**
 * Get Bedrock Chat parameters based on environment name.
 * If you omit envName, "default" is used.
 * If you omit parametersInput, context parameters and environment variables are used.
 * @param app CDK App instance
 * @param envName (optional) Environment name. Used as map key if provided
 * @param paramsMap (optional) Map of parameters. If not provided, use context parameters
 * @returns Validated parameters object
 */
export function getBedrockChatParameters(
  app: App,
  envName: string | undefined,
  paramsMap: Map<string, BedrockChatParametersInput>
): BedrockChatParameters {
  if (envName == undefined) {
    if (paramsMap.has("default")) {
      // Use parameter.ts instead of context parameters
      const params = paramsMap.get("default") || {};
      return resolveBedrockChatParameters(app, {
        envName: "default",
        envPrefix: "",
        ...params,
      });
    } else {
      // Use CDK context parameters (cdk.json or -c options)
      return resolveBedrockChatParameters(app);
    }
  } else {
    // Lookup envName in parameter.ts
    if (!paramsMap.has(envName)) {
      throw new Error(`Environment ${envName} not found in parameter.ts`);
    }

    const params = paramsMap.get(envName) || {};
    const envPrefix = envName === "default" ? "" : envName;

    return resolveBedrockChatParameters(app, {
      envName,
      envPrefix,
      ...params,
    });
  }
}

/**
 * Parse and validate parameters for API publishing.
 * This function is executed by CDK in CodeBuild launched via the API.
 * Therefore, this is not intend to be set values using cdk.json or parameter.ts.
 * @returns Validated parameters object from environment variables
 */
export function resolveApiPublishParameters(): ApiPublishParameters {
  const envVars = {
    envName: getEnvVar("ENV_NAME"),
    envPrefix: getEnvVar("ENV_PREFIX"),
    bedrockRegion: getEnvVar("BEDROCK_REGION"),
    enableBedrockGlobalInference: getBooleanEnvVar(
      "ENABLE_BEDROCK_GLOBAL_INFERENCE"
    ),
    enableBedrockCrossRegionInference: getBooleanEnvVar(
      "ENABLE_BEDROCK_CROSS_REGION_INFERENCE"
    ),
    publishedApiThrottleRateLimit: getEnvVar(
      "PUBLISHED_API_THROTTLE_RATE_LIMIT"
    ),
    publishedApiThrottleBurstLimit: getEnvVar(
      "PUBLISHED_API_THROTTLE_BURST_LIMIT"
    ),
    publishedApiQuotaLimit: getEnvVar("PUBLISHED_API_QUOTA_LIMIT"),
    publishedApiQuotaPeriod: getEnvVar("PUBLISHED_API_QUOTA_PERIOD"),
    publishedApiDeploymentStage: getEnvVar("PUBLISHED_API_DEPLOYMENT_STAGE"),
    publishedApiId: getEnvVar("PUBLISHED_API_ID"),
    publishedApiAllowedOrigins: getEnvVar("PUBLISHED_API_ALLOWED_ORIGINS"),
    globalAvailableModels: getEnvVar("GLOBAL_AVAILABLE_MODELS"),
    defaultModel: getEnvVar("DEFAULT_MODEL"),
    titleModel: getEnvVar("TITLE_MODEL"),
  };

  return ApiPublishParametersSchema.parse(envVars);
}

/**
 * Parse and validate parameters for Bedrock Custom Bot.
 * This function is executed by CDK in CodeBuild launched via the API.
 * Therefore, this is not intend to be set values using cdk.json or parameter.ts.
 * @returns Validated parameters object from environment variables
 */
export function resolveBedrockCustomBotParameters(): BedrockCustomBotParameters {
  const envVars = {
    envName: getEnvVar("ENV_NAME"),
    envPrefix: getEnvVar("ENV_PREFIX"),
    bedrockRegion: getEnvVar("BEDROCK_REGION"),
    ownerUserId: getEnvVar("OWNER_USER_ID"),
    botId: getEnvVar("BOT_ID"),
    documentBucketName: getEnvVar("BEDROCK_CLAUDE_CHAT_DOCUMENT_BUCKET_NAME"),
    knowledge: getEnvVar("KNOWLEDGE"),
    knowledgeBase: getEnvVar("KNOWLEDGE_BASE"),
    guardrails: getEnvVar("GUARDRAILS"),
    enableRagReplicas: getEnvVar("ENABLE_RAG_REPLICAS"),
  };

  return BedrockCustomBotParametersSchema.parse(envVars);
}

/**
 * Parse and validate parameters for shared Knowledge Bases.
 * This function is executed by CDK in CodeBuild launched via the API.
 * Therefore, this is not intend to be set values using cdk.json or parameter.ts.
 * @returns Validated parameters object from environment variables
 */
export function resolveBedrockSharedKnowledgeBasesParameters(): BedrockSharedKnowledgeBasesParameters {
  const envVars = {
    envName: getEnvVar("ENV_NAME"),
    envPrefix: getEnvVar("ENV_PREFIX"),
    bedrockRegion: getEnvVar("BEDROCK_REGION"),
    sharedKnowledgeBases: getEnvVar("SHARED_KNOWLEDGE_BASES"),
    documentBucketName: getEnvVar("BEDROCK_CLAUDE_CHAT_DOCUMENT_BUCKET_NAME"),
    enableRagReplicas: getEnvVar("ENABLE_RAG_REPLICAS"),
  };

  return BedrockSharedKnowledgeBasesParametersSchema.parse(envVars);
}
