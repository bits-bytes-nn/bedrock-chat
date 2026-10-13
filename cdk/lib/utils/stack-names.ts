/**
 * Prefix of the stacks of published APIs, followed by the published API ID (the bot
 * ID). The backend repeats this literal.
 */
export const apiPublishmentStackPrefix = "ApiPublishmentStack";

/**
 * Prefix of the stacks of bots with a dedicated knowledge base, in the Bedrock Region,
 * followed by the bot ID. The backend repeats this literal.
 */
export const customBotStackPrefix = "BrChatKbStack";

/**
 * Name of the stack with the shared knowledge bases, in the Bedrock Region. Each
 * environment has its own; the default environment keeps the unprefixed name of
 * existing deployments.
 */
export const sharedKnowledgeBasesStackName = (envPrefix: string): string =>
  `${envPrefix}${envPrefix ? "-" : ""}BrChatSharedKbStack`;
