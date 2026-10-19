import * as iam from "aws-cdk-lib/aws-iam";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";

/** The internet search of chats without a bot. */
export interface DefaultChatSearch {
  /** The engine, or empty for no search. */
  readonly engine: string;
  /** The API key of an engine that needs one. */
  readonly apiKey?: secretsmanager.ISecret;
}

/**
 * Lets a chat handler search for chats without a bot: grants it the API key and
 * returns its environment variables.
 */
export function defaultChatSearchEnvironment(
  search: DefaultChatSearch,
  role: iam.IGrantable
): Record<string, string> {
  search.apiKey?.grantRead(role);
  return {
    DEFAULT_CHAT_SEARCH_ENGINE: search.engine,
    DEFAULT_CHAT_SEARCH_API_KEY_SECRET_ARN: search.apiKey?.secretArn ?? "",
  };
}
