/**
 * IAM path of the roles that may assume the table access role. A path is set only
 * when a role is created, so, unlike names (which CloudFormation shortens for long
 * stack names) or tags (which session tags can supply), it identifies these roles.
 */
export const tableAccessRolePath = (envPrefix: string): string =>
  `/bedrock-chat/${envPrefix || "default"}/`;
