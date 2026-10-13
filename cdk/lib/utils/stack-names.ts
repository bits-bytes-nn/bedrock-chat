/**
 * Name of the stack with the shared knowledge bases, in the Bedrock Region. Each
 * environment has its own; the default environment keeps the unprefixed name of
 * existing deployments.
 */
export const sharedKnowledgeBasesStackName = (envPrefix: string): string =>
  `${envPrefix}${envPrefix ? "-" : ""}BrChatSharedKbStack`;
