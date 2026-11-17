/**
 * Prefix of the stacks of published APIs, followed by the published API ID (the bot
 * ID). backend/app/utils.py repeats this literal.
 */
export const apiPublishmentStackPrefix = "ApiPublishmentStack";

/**
 * Prefix of the stacks of bots with a dedicated knowledge base, in the Bedrock Region,
 * followed by the bot ID. backend/app/utils.py repeats this literal.
 */
export const customBotStackPrefix = "BrChatKbStack";

/**
 * Name of the stack with the shared knowledge bases, in the Bedrock Region. Each
 * environment has its own; the default environment keeps the unprefixed name of
 * existing deployments.
 */
export const sharedKnowledgeBasesStackName = (envPrefix: string): string =>
  `${envPrefix}${envPrefix ? "-" : ""}BrChatSharedKbStack`;

/** The chat stack's exports that the published API stacks import. */
const CHAT_STACK_EXPORTS = {
  publishedApiWebAclArn: "PublishedApiWebAclArn",
  conversationTableName: "BedrockClaudeChatConversationTableName",
  botTableName: "BedrockClaudeChatBotTableNameV3",
  tableAccessRoleArn: "BedrockClaudeChatTableAccessRoleArn",
  largeMessageBucketName: "BedrockClaudeChatLargeMessageBucketName",
  alarmTopicArn: "BedrockClaudeChatAlarmTopicArn",
} as const;

/** The export name of a chat stack output that published API stacks import. */
export const chatStackExportName = (
  envPrefix: string,
  output: keyof typeof CHAT_STACK_EXPORTS
): string =>
  `${envPrefix}${envPrefix ? "-" : ""}${CHAT_STACK_EXPORTS[output]}`;
