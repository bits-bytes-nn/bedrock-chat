#!/usr/bin/env node
import { metricsNamespace } from "../lib/utils/metrics";
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { ApiPublishmentStack } from "../lib/api-publishment-stack";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import { resolveApiPublishParameters } from "../lib/utils/parameter-models";

const app = new cdk.App();

// Get parameters specific to API publishing
const params = resolveApiPublishParameters();
const sepHyphen = params.envPrefix ? "-" : "";

// Parse allowed origins
const publishedApiAllowedOrigins = JSON.parse(
  params.publishedApiAllowedOrigins || '["*"]'
);

// Log all parameters at once for debugging

const webAclArn = cdk.Fn.importValue(
  `${params.envPrefix}${sepHyphen}PublishedApiWebAclArn`
);

const conversationTableName = cdk.Fn.importValue(
  `${params.envPrefix}${sepHyphen}BedrockClaudeChatConversationTableName`
);
const botTableName = cdk.Fn.importValue(
  `${params.envPrefix}${sepHyphen}BedrockClaudeChatBotTableNameV3`
);
const tableAccessRoleArn = cdk.Fn.importValue(
  `${params.envPrefix}${sepHyphen}BedrockClaudeChatTableAccessRoleArn`
);
const largeMessageBucketName = cdk.Fn.importValue(
  `${params.envPrefix}${sepHyphen}BedrockClaudeChatLargeMessageBucketName`
);

const alarmTopicArn = cdk.Fn.importValue(
  `${params.envPrefix}${sepHyphen}BedrockClaudeChatAlarmTopicArn`
);

// Applied when the publisher sets no throttling.
const DEFAULT_PUBLISHED_API_THROTTLE = { rateLimit: 10, burstLimit: 20 };

// NOTE: DO NOT change the stack id naming rule.
new ApiPublishmentStack(app, `ApiPublishmentStack${params.publishedApiId}`, {
  env: {
    region: process.env.CDK_DEFAULT_REGION,
  },
  bedrockRegion: params.bedrockRegion,
  metricsNamespace: metricsNamespace(params.envPrefix),
  alarmTopicArn,
  enableBedrockGlobalInference: params.enableBedrockGlobalInference,
  enableBedrockCrossRegionInference: params.enableBedrockCrossRegionInference,
  conversationTableName: conversationTableName,
  botTableName: botTableName,
  tableAccessRoleArn: tableAccessRoleArn,
  webAclArn: webAclArn,
  largeMessageBucketName: largeMessageBucketName,
  modelEnvironment: {
    GLOBAL_AVAILABLE_MODELS: params.globalAvailableModels,
    DEFAULT_MODEL: params.defaultModel,
    TITLE_MODEL: params.titleModel,
  },
  usagePlan: {
    // Without a limit, a leaked API key could run up model costs at the account's
    // full API Gateway quota.
    throttle:
      params.publishedApiThrottleRateLimit !== undefined &&
      params.publishedApiThrottleBurstLimit !== undefined
        ? {
            rateLimit: params.publishedApiThrottleRateLimit,
            burstLimit: params.publishedApiThrottleBurstLimit,
          }
        : DEFAULT_PUBLISHED_API_THROTTLE,
    quota:
      params.publishedApiQuotaLimit !== undefined &&
      params.publishedApiQuotaPeriod !== undefined
        ? {
            limit: params.publishedApiQuotaLimit,
            period: apigateway.Period[params.publishedApiQuotaPeriod],
          }
        : undefined,
  },
  deploymentStage: params.publishedApiDeploymentStage,
  corsOptions: {
    allowOrigins: publishedApiAllowedOrigins,
    allowMethods: apigateway.Cors.ALL_METHODS,
    allowHeaders: apigateway.Cors.DEFAULT_HEADERS,
    allowCredentials: true,
  },
});

cdk.Tags.of(app).add("CDKEnvironment", params.envName);
