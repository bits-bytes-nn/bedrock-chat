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
      "bedrock:IngestKnowledgeBaseDocuments",
      "bedrock:DeleteKnowledgeBaseDocuments",
    ],
    resources: ["*"],
  });
