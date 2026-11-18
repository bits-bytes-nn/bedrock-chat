import { Aws } from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";

/** The internet search of chats without a bot. */
export interface DefaultChatSearch {
  /** The engine, or empty for no search. */
  readonly engine: string;
  /** The API key of an engine that needs one. */
  readonly apiKey?: secretsmanager.ISecret;
  /** The Region of AgentCore Web Search, which bots can choose too. */
  readonly webSearchRegion: string;
}

/**
 * Lets a chat handler search with AgentCore Web Search, an engine without an API
 * key that any bot can choose, and returns its environment variables.
 */
export function webSearchEnvironment(
  region: string,
  role: iam.IGrantable
): Record<string, string> {
  role.grantPrincipal.addToPrincipalPolicy(
    new iam.PolicyStatement({
      actions: ["bedrock-agentcore:InvokeWebSearch"],
      // The AWS managed tool: the account field is the literal "aws".
      resources: [
        `arn:${Aws.PARTITION}:bedrock-agentcore:${region}:aws:tool/web-search.v1`,
      ],
    })
  );
  return { WEB_SEARCH_REGION: region };
}

/**
 * Lets a chat handler search the internet: grants it the API key of chats without
 * a bot and AgentCore Web Search, and returns its environment variables.
 */
export function defaultChatSearchEnvironment(
  search: DefaultChatSearch,
  role: iam.IGrantable
): Record<string, string> {
  search.apiKey?.grantRead(role);
  return {
    DEFAULT_CHAT_SEARCH_ENGINE: search.engine,
    DEFAULT_CHAT_SEARCH_API_KEY_SECRET_ARN: search.apiKey?.secretArn ?? "",
    ...webSearchEnvironment(search.webSearchRegion, role),
  };
}
