#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { BedrockChatStack } from "../lib/bedrock-chat-stack";
import { BedrockRegionResourcesStack } from "../lib/bedrock-region-resources";
import { FrontendWafStack } from "../lib/frontend-waf-stack";
import { LogRetentionChecker } from "../rules/log-retention-checker";
import { getBedrockChatParameters } from "../lib/utils/parameter-models";
import { bedrockChatParams } from "../parameter";

const app = new cdk.App();

// Specify env name by "envName" context variable
// ex) cdk synth -c envName=foo
// If you don't specify the envName context variable, "default" is used.
const params = getBedrockChatParameters(
  app,
  app.node.tryGetContext("envName"),
  bedrockChatParams
);

const sepHyphen = params.envPrefix ? "-" : "";

let waf: FrontendWafStack | undefined;
if (params.enableFrontendWaf) {
  // WAF for frontend
  // A WAF for CloudFront must be created in us-east-1, so it has its own stack.
  // https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-wafv2-webacl.html
  waf = new FrontendWafStack(
    app,
    `${params.envPrefix}${sepHyphen}FrontendWafStack`,
    {
      env: {
        region: "us-east-1",
      },
      envPrefix: params.envPrefix,
      allowedIpV4AddressRanges: params.allowedIpV4AddressRanges,
      allowedIpV6AddressRanges: params.allowedIpV6AddressRanges,
    }
  );
}

// The region of the LLM model called by the converse API and the region of Guardrail must be in the same region.
// CustomBotStack contains Knowledge Bases is deployed in the same region as the LLM model, and source bucket must be in the same region as Knowledge Bases.
// Therefore, define BedrockRegionResourcesStack containing the source bucket in the same region as the LLM model.
// Ref: https://docs.aws.amazon.com/bedrock/latest/userguide/s3-data-source-connector.html
const bedrockRegionResources = new BedrockRegionResourcesStack(
  app,
  `${params.envPrefix}${sepHyphen}BedrockRegionResourcesStack`,
  {
    env: {
      region: params.bedrockRegion,
    },
    crossRegionReferences: true,
  }
);

const chat = new BedrockChatStack(
  app,
  `${params.envPrefix}${sepHyphen}BedrockChatStack`,
  {
    env: {
      region: process.env.CDK_DEFAULT_REGION,
    },
    envName: params.envName,
    envPrefix: params.envPrefix,
    crossRegionReferences: true,
    bedrockRegion: params.bedrockRegion,
    webAclId: waf ? waf.webAclArn.value : '',
    enableIpV6: params.enableFrontendIpv6 && params.allowedIpV6AddressRanges.length > 0,
    identityProviders: params.identityProviders,
    userPoolDomainPrefix: params.userPoolDomainPrefix,
    publishedApiAllowedIpV4AddressRanges:
      params.publishedApiAllowedIpV4AddressRanges,
    publishedApiAllowedIpV6AddressRanges:
      params.publishedApiAllowedIpV6AddressRanges,
    allowedIpV4AddressRanges: params.allowedIpV4AddressRanges,
    allowedIpV6AddressRanges: params.allowedIpV6AddressRanges,
    allowedSignUpEmailDomains: params.allowedSignUpEmailDomains,
    autoJoinUserGroups: params.autoJoinUserGroups,
    selfSignUpEnabled: params.selfSignUpEnabled,
    documentBucket: bedrockRegionResources.documentBucket,
    enableRagReplicas: params.enableRagReplicas,
    enableBedrockGlobalInference: params.enableBedrockGlobalInference,
    enableBedrockCrossRegionInference: params.enableBedrockCrossRegionInference,
    enableLambdaSnapStart: params.enableLambdaSnapStart,
    alternateDomainName: params.alternateDomainName,
    hostedZoneId: params.hostedZoneId,
    enableBotStore: params.enableBotStore,
    enableBotStoreReplicas: params.enableBotStoreReplicas,
    botStoreLanguage: params.botStoreLanguage,
    globalAvailableModels: params.globalAvailableModels,
    defaultModel: params.defaultModel,
    titleModel: params.titleModel,
    tokenValidMinutes: params.tokenValidMinutes,
    devAccessIamRoleArn: params.devAccessIamRoleArn,
    allowedCountries: params.allowedCountries,
    logoPath: params.logoPath,
    alarmEmail: params.alarmEmail,
    dailyChatCostAlarmUsd: params.dailyChatCostAlarmUsd,
    maxDedicatedKnowledgeBasesPerUser: params.maxDedicatedKnowledgeBasesPerUser,
    usageAnalysisRetentionDays: params.usageAnalysisRetentionDays,
    apiThrottle: {
      rateLimit: params.apiThrottleRateLimit,
      burstLimit: params.apiThrottleBurstLimit,
    },
  }
);
if (waf) {
  chat.addDependency(waf);
}
chat.addDependency(bedrockRegionResources);

cdk.Aspects.of(chat).add(new LogRetentionChecker());
cdk.Tags.of(app).add("CDKEnvironment", params.envName);
