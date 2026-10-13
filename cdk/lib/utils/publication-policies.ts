import { Stack } from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";

/**
 * CloudFormation actions on the per-bot stacks that the backend manages:
 * published APIs in the app Region and knowledge bases in the Bedrock Region.
 */
export const botStackPolicyStatement = (
  stack: Stack,
  botStacks: { readonly stackNamePrefix: string; readonly region: string }[]
): iam.PolicyStatement =>
  new iam.PolicyStatement({
    actions: [
      "cloudformation:DescribeStacks",
      "cloudformation:DescribeStackEvents",
      "cloudformation:DescribeStackResource",
      "cloudformation:DescribeStackResources",
      "cloudformation:DeleteStack",
    ],
    resources: botStacks.map(
      ({ stackNamePrefix, region }) =>
        `arn:${stack.partition}:cloudformation:${region}:${stack.account}:stack/${stackNamePrefix}*/*`
    ),
  });

/** API Gateway actions on the API keys and usage plans of published APIs. */
export const publishedApiKeyPolicyStatement = (
  stack: Stack
): iam.PolicyStatement =>
  new iam.PolicyStatement({
    actions: [
      "apigateway:GET",
      "apigateway:POST",
      "apigateway:PUT",
      "apigateway:DELETE",
    ],
    resources: ["/apikeys", "/apikeys/*", "/usageplans/*"].map(
      (path) => `arn:${stack.partition}:apigateway:${stack.region}::${path}`
    ),
  });
