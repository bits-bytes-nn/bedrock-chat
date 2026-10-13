import { Tags } from "aws-cdk-lib";
import { IConstruct } from "constructs";

/**
 * Tag on the roles that may assume the table access role. Generated role names keep
 * the stack name only when it is short, so the trust policy does not rely on names
 * alone.
 */
export const TABLE_ACCESS_TAG_KEY = "bedrock-chat:table-access";

export const tableAccessTagValue = (envPrefix: string): string =>
  envPrefix || "default";

/** Tag every role in the scope as allowed to assume the table access role. */
export const tagTableAccessRoles = (scope: IConstruct, envPrefix: string) =>
  Tags.of(scope).add(TABLE_ACCESS_TAG_KEY, tableAccessTagValue(envPrefix), {
    includeResourceTypes: ["AWS::IAM::Role"],
  });
