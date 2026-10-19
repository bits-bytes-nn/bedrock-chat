import { Stack } from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";

/**
 * Bedrock actions used to answer chats: model invocation (Converse and
 * ConverseStream), inference profile lookup, guardrails, knowledge base
 * retrieval and Bedrock Agents. Resources stay "*" because inference profiles
 * route to foundation models in other Regions.
 */
export const bedrockChatPolicyStatement = (): iam.PolicyStatement =>
  new iam.PolicyStatement({
    actions: [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
      "bedrock:ListInferenceProfiles",
      "bedrock:ApplyGuardrail",
      "bedrock:GetKnowledgeBase",
      "bedrock:Retrieve",
      "bedrock:GetAgent",
      "bedrock:InvokeAgent",
    ],
    resources: ["*"],
  });

/** Bedrock actions used to synchronize knowledge base data sources. */
export const bedrockIngestionPolicyStatement = (): iam.PolicyStatement =>
  new iam.PolicyStatement({
    actions: [
      "bedrock:GetDataSource",
      "bedrock:StartIngestionJob",
      "bedrock:GetIngestionJob",
      "bedrock:GetKnowledgeBaseDocuments",
      "bedrock:ListKnowledgeBaseDocuments",
      "bedrock:IngestKnowledgeBaseDocuments",
      "bedrock:DeleteKnowledgeBaseDocuments",
    ],
    resources: ["*"],
  });

/**
 * The internet search engines that need an API key, as in SEARCH_API_MAX_RESULTS
 * of backend/app/routes/schemas/bot.py.
 */
export const SEARCH_API_ENGINES = ["firecrawl", "tavily", "brave"] as const;

/**
 * Secrets Manager actions on the search API keys of bots with the internet
 * search tool, which the backend stores as `<engine>/<user id>/<bot id>`.
 */
export const searchApiKeySecretPolicyStatement = (
  stack: Stack,
  actions: string[]
): iam.PolicyStatement =>
  new iam.PolicyStatement({
    actions,
    resources: SEARCH_API_ENGINES.map(
      (engine) =>
        `arn:${stack.partition}:secretsmanager:${stack.region}:${stack.account}:secret:${engine}/*/*`
    ),
  });
