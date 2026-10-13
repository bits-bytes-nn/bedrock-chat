import * as cdk from "aws-cdk-lib";
import { BedrockChatStack } from "../lib/bedrock-chat-stack";
import { Template } from "aws-cdk-lib/assertions";
import {
  getEmbeddingModel,
  getChunkingStrategy,
  getChunkingOptions,
  getAnalyzer,
  getKnowledgeBaseType,
} from "../lib/utils/bedrock-knowledge-base-args";
import { BedrockCustomBotStack } from "../lib/bedrock-custom-bot-stack";
import { BedrockRegionResourcesStack } from "../lib/bedrock-region-resources";
import { ApiPublishmentStack } from "../lib/api-publishment-stack";
import { BedrockSharedKnowledgeBasesStack } from "../lib/bedrock-shared-knowledge-bases-stack";
import { Match } from "aws-cdk-lib/assertions";

// Skip asset bundling. It runs Docker for every synth and the tests do not inspect assets.
const testAppProps: cdk.AppProps = {
  context: { "aws:cdk:bundling-stacks": [] },
};

describe("Bedrock Chat Stack Test", () => {
  test("Identity Provider Generation", () => {
    const app = new cdk.App(testAppProps);

    const domainPrefix = "test-domain";

    const bedrockRegionResourcesStack = new BedrockRegionResourcesStack(
      app,
      "BedrockRegionResourcesStack",
      {
        env: {
          region: "us-east-1",
        },
        crossRegionReferences: true,
      }
    );

    const hasGoogleProviderStack = new BedrockChatStack(
      app,
      "IdentityProviderGenerateStack",
      {
        env: {
          region: "us-west-2",
        },
        envName: "test",
        envPrefix: "test-",
        bedrockRegion: "us-east-1",
        crossRegionReferences: true,
        webAclId: "",
        identityProviders: [
          {
            secretName: "MyTestSecret",
            service: "google",
          },
        ],
        userPoolDomainPrefix: domainPrefix,
        publishedApiAllowedIpV4AddressRanges: [""],
        publishedApiAllowedIpV6AddressRanges: [""],
        allowedIpV4AddressRanges: [""],
        allowedIpV6AddressRanges: [""],
        allowedSignUpEmailDomains: [],
        autoJoinUserGroups: [],
        selfSignUpEnabled: true,
        enableIpV6: true,
        documentBucket: bedrockRegionResourcesStack.documentBucket,
        enableRagReplicas: false,
        enableBedrockGlobalInference: false,
        enableBedrockCrossRegionInference: false,
        enableLambdaSnapStart: true,
        enableBotStore: true,
        enableBotStoreReplicas: false,
        botStoreLanguage: "en",
        tokenValidMinutes: 60,
        alarmEmail: "",
        dailyChatCostAlarmUsd: 100,
        maxDedicatedKnowledgeBasesPerUser: 2,
        usageAnalysisRetentionDays: 90,
        apiThrottle: { rateLimit: 500, burstLimit: 1000 },
      }
    );
    const hasGoogleProviderTemplate = Template.fromStack(
      hasGoogleProviderStack
    );

    hasGoogleProviderTemplate.hasResourceProperties(
      "AWS::Cognito::UserPoolDomain",
      {
        Domain: domainPrefix,
      }
    );
    hasGoogleProviderTemplate.hasResourceProperties(
      "AWS::Cognito::UserPoolClient",
      {
        SupportedIdentityProviders: ["Google", "COGNITO"],
      }
    );
    hasGoogleProviderTemplate.hasResourceProperties(
      "AWS::Cognito::UserPoolIdentityProvider",
      {
        ProviderName: "Google",
        ProviderType: "Google",
      }
    );
  });

  test("Custom OIDC Provider Generation", () => {
    const app = new cdk.App(testAppProps);
    const domainPrefix = "test-domain";

    const bedrockRegionResourcesStack = new BedrockRegionResourcesStack(
      app,
      "BedrockRegionResourcesStack",
      {
        env: {
          region: "us-east-1",
        },
        crossRegionReferences: true,
      }
    );

    const hasOidcProviderStack = new BedrockChatStack(
      app,
      "OidcProviderGenerateStack",
      {
        env: {
          region: "us-west-2",
        },
        envName: "test",
        envPrefix: "test-",
        bedrockRegion: "us-east-1",
        crossRegionReferences: true,
        webAclId: "",
        identityProviders: [
          {
            secretName: "MyOidcTestSecret",
            service: "oidc",
            serviceName: "MyOidcProvider",
          },
        ],
        userPoolDomainPrefix: domainPrefix,
        publishedApiAllowedIpV4AddressRanges: [""],
        publishedApiAllowedIpV6AddressRanges: [""],
        allowedSignUpEmailDomains: [],
        autoJoinUserGroups: [],
        allowedIpV4AddressRanges: [""],
        allowedIpV6AddressRanges: [""],
        selfSignUpEnabled: true,
        enableIpV6: true,
        documentBucket: bedrockRegionResourcesStack.documentBucket,
        enableRagReplicas: false,
        enableBedrockGlobalInference: false,
        enableBedrockCrossRegionInference: false,
        enableLambdaSnapStart: true,
        enableBotStore: true,
        enableBotStoreReplicas: false,
        botStoreLanguage: "en",
        tokenValidMinutes: 60,
        alarmEmail: "",
        dailyChatCostAlarmUsd: 100,
        maxDedicatedKnowledgeBasesPerUser: 2,
        usageAnalysisRetentionDays: 90,
        apiThrottle: { rateLimit: 500, burstLimit: 1000 },
      }
    );
    const hasOidcProviderTemplate = Template.fromStack(hasOidcProviderStack);

    hasOidcProviderTemplate.hasResourceProperties(
      "AWS::Cognito::UserPoolDomain",
      {
        Domain: domainPrefix,
      }
    );

    hasOidcProviderTemplate.hasResourceProperties(
      "AWS::Cognito::UserPoolClient",
      {
        SupportedIdentityProviders: ["MyOidcProvider", "COGNITO"],
      }
    );
    hasOidcProviderTemplate.hasResourceProperties(
      "AWS::Cognito::UserPoolIdentityProvider",
      {
        ProviderType: "OIDC",
      }
    );
  });

  test("default stack", () => {
    const app = new cdk.App(testAppProps);

    const bedrockRegionResourcesStack = new BedrockRegionResourcesStack(
      app,
      "BedrockRegionResourcesStack",
      {
        env: {
          region: "us-east-1",
        },
        crossRegionReferences: true,
      }
    );

    const stack = new BedrockChatStack(app, "MyTestStack", {
      env: {
        region: "us-west-2",
      },
      envName: "test",
      envPrefix: "test-",
      bedrockRegion: "us-east-1",
      crossRegionReferences: true,
      webAclId: "",
      identityProviders: [],
      userPoolDomainPrefix: "",
      publishedApiAllowedIpV4AddressRanges: [""],
      publishedApiAllowedIpV6AddressRanges: [""],
      allowedSignUpEmailDomains: [],
      autoJoinUserGroups: [],
      selfSignUpEnabled: true,
      enableIpV6: true,
      allowedIpV4AddressRanges: [""],
      allowedIpV6AddressRanges: [""],
      documentBucket: bedrockRegionResourcesStack.documentBucket,
      enableRagReplicas: false,
      enableBedrockGlobalInference: false,
      enableBedrockCrossRegionInference: false,
      enableLambdaSnapStart: true,
      enableBotStore: true,
      enableBotStoreReplicas: false,
      botStoreLanguage: "en",
      tokenValidMinutes: 60,
      alarmEmail: "",
      dailyChatCostAlarmUsd: 100,
      maxDedicatedKnowledgeBasesPerUser: 2,
      usageAnalysisRetentionDays: 90,
      apiThrottle: { rateLimit: 500, burstLimit: 1000 },
    });
    const template = Template.fromStack(stack);

    template.resourceCountIs("AWS::Cognito::UserPoolIdentityProvider", 0);

    // User data survives stack deletion. The WebSocket session table is temporary.
    template.resourcePropertiesCountIs(
      "AWS::DynamoDB::Table",
      { DeletionProtectionEnabled: true },
      2
    );
    template.hasResource("AWS::Cognito::UserPool", {
      DeletionPolicy: "Retain",
      Properties: Match.objectLike({ DeletionProtection: "ACTIVE" }),
    });

    // Lambda roles must not get the Bedrock control plane.
    const policies = template.findResources("AWS::IAM::Policy");
    const actions = Object.values(policies).flatMap((policy: any) =>
      policy.Properties.PolicyDocument.Statement.flatMap((statement: any) =>
        [statement.Action].flat()
      )
    );
    expect(actions).not.toContain("bedrock:*");

    // Document uploads are allowed from CloudFront, not from every origin.
    const regionTemplate = Template.fromStack(bedrockRegionResourcesStack);
    const bucketCors = Object.values(
      regionTemplate.findResources("AWS::S3::Bucket")
    ).flatMap((bucket: any) =>
      (bucket.Properties.CorsConfiguration?.CorsRules ?? []).flatMap(
        (rule: any) => rule.AllowedOrigins
      )
    );
    expect(bucketCors).toContain("https://*.cloudfront.net");
    expect(bucketCors).not.toContain("*");
    expect(bucketCors.join()).not.toContain("undefined");

    // Stack deletion and API Gateway access are limited to the per-bot resources.
    const statements = Object.values(policies).flatMap(
      (policy: any) => policy.Properties.PolicyDocument.Statement
    );
    for (const statement of statements) {
      const statementActions = [statement.Action].flat();
      if (
        statementActions.some(
          (action: string) =>
            action === "cloudformation:DeleteStack" ||
            action.startsWith("apigateway:")
        )
      ) {
        expect([statement.Resource].flat()).not.toContain("*");
      }
    }

    // Access logs expire, and the projects that deploy bot and API stacks log to a
    // group with retention.
    for (const accessLogTemplate of [template, regionTemplate]) {
      accessLogTemplate.hasResourceProperties("AWS::S3::Bucket", {
        LifecycleConfiguration: {
          Rules: [{ ExpirationInDays: 90, Status: "Enabled" }],
        },
      });
    }
    const deployProjects = Object.values(
      template.findResources("AWS::CodeBuild::Project", {
        Properties: { Source: Match.objectLike({ Type: "S3" }) },
      })
    );
    expect(deployProjects).toHaveLength(3);
    for (const project of deployProjects as any[]) {
      expect(
        project.Properties.LogsConfig.CloudWatchLogs.GroupName
      ).toBeDefined();
    }
    template.resourcePropertiesCountIs(
      "AWS::Logs::LogGroup",
      { RetentionInDays: 90 },
      // The three deploy projects, the API access logs and the state machine logs.
      5
    );

    // Secrets, bot store search and stack lookups are scoped to the resources that
    // the backend calls.
    for (const statement of statements) {
      const statementActions = [statement.Action].flat();
      if (
        statementActions.some(
          (action: string) =>
            action.startsWith("secretsmanager:") ||
            action.startsWith("cloudformation:")
        ) ||
        statement.Action === "aoss:APIAccessAll"
      ) {
        expect([statement.Resource].flat()).not.toContain("*");
      }
    }
    expect(actions).toContain("aoss:APIAccessAll");
    expect(actions).not.toContain("secretsmanager:RotateSecret");
    expect(actions).not.toContain("aoss:ListCollections");

    // Alarms and API throttling.
    template.resourceCountIs("AWS::CloudWatch::Alarm", 8);
    // Usage exports hold conversation text, so they expire.
    template.hasResourceProperties("AWS::S3::Bucket", {
      LifecycleConfiguration: {
        Rules: [Match.objectLike({ ExpirationInDays: 90, Status: "Enabled" })],
      },
    });
    template.hasResourceProperties("AWS::CloudWatch::Alarm", {
      // Per environment (cdk/lib/utils/metrics.ts).
      Namespace: Match.stringLikeRegexp("^BedrockChat"),
      MetricName: "ChatCost",
      Statistic: "Sum",
      Period: 86400,
      Threshold: 100,
    });
    // Cost guards: connections need a token, and bots with their own knowledge
    // base are limited per user.
    template.hasResourceProperties("AWS::ApiGatewayV2::Authorizer", {
      AuthorizerType: "REQUEST",
      IdentitySource: ["route.request.querystring.token"],
    });
    template.hasResourceProperties("AWS::Lambda::Function", {
      Environment: {
        Variables: Match.objectLike({ MAX_DEDICATED_KNOWLEDGE_BASES_PER_USER: "2" }),
      },
    });
    template.hasResourceProperties("AWS::CloudWatch::Alarm", {
      Namespace: "AWS/Lambda",
      MetricName: "Errors",
      Statistic: "Sum",
    });
    // Handlers answer errors without failing, so chat errors and failed bot syncs
    // are counted from their logs.
    template.resourceCountIs("AWS::Logs::MetricFilter", 2);
    // Failed bot removals are kept for investigation instead of being dropped.
    template.hasResourceProperties("AWS::Lambda::EventSourceMapping", {
      DestinationConfig: Match.objectLike({ OnFailure: Match.anyValue() }),
    });
    template.hasResourceProperties("AWS::CloudFront::Distribution", {
      DistributionConfig: Match.objectLike({
        DefaultCacheBehavior: Match.objectLike({
          ResponseHeadersPolicyId: Match.anyValue(),
        }),
      }),
    });
    // Browsers revalidate index.html, so a deployment does not leave them with
    // references to removed chunks. Hashed assets stay cached.
    template.hasResourceProperties("AWS::CloudFront::ResponseHeadersPolicy", {
      ResponseHeadersPolicyConfig: Match.objectLike({
        CustomHeadersConfig: {
          Items: [{ Header: "Cache-Control", Value: "no-cache", Override: true }],
        },
        SecurityHeadersConfig: Match.objectLike({
          ContentSecurityPolicy: Match.anyValue(),
          StrictTransportSecurity: Match.anyValue(),
        }),
      }),
    });
    template.hasResourceProperties("AWS::CloudFront::Distribution", {
      DistributionConfig: Match.objectLike({
        CacheBehaviors: [
          Match.objectLike({
            PathPattern: "/assets/*",
            CachePolicyId: "658327ea-f89d-4fab-a63d-7e88639e58f6",
            ResponseHeadersPolicyId: Match.anyValue(),
          }),
        ],
      }),
    });
    template.hasResourceProperties("AWS::ApiGatewayV2::Stage", {
      StageName: "dev",
      DefaultRouteSettings: Match.objectLike({ ThrottlingRateLimit: 500 }),
    });
    template.hasResourceProperties("AWS::ApiGatewayV2::Stage", {
      StageName: "$default",
      DefaultRouteSettings: Match.objectLike({ ThrottlingBurstLimit: 1000 }),
      AccessLogSettings: Match.objectLike({ DestinationArn: Match.anyValue() }),
    });
    expect(actions).toContain("bedrock:InvokeModelWithResponseStream");

    // The main API accepts requests from the app and the local development server only.
    const httpApi = Object.values(
      template.findResources("AWS::ApiGatewayV2::Api", {
        Properties: { ProtocolType: "HTTP" },
      })
    )[0] as any;
    const apiOrigins = httpApi.Properties.CorsConfiguration.AllowOrigins;
    expect(apiOrigins).not.toContain("*");
    expect(apiOrigins).toContain("http://localhost:5173");
    expect(JSON.stringify(apiOrigins)).toContain("DomainName");
  });

  test("custom domain configuration", () => {
    const app = new cdk.App(testAppProps);

    const bedrockRegionResourcesStack = new BedrockRegionResourcesStack(
      app,
      "BedrockRegionResourcesStack",
      {
        env: {
          region: "us-east-1",
        },
        crossRegionReferences: true,
      }
    );

    const customDomainStack = new BedrockChatStack(app, "CustomDomainStack", {
      env: {
        region: "us-east-1",
      },
      envName: "test",
      envPrefix: "test-",
      bedrockRegion: "us-east-1",
      crossRegionReferences: true,
      webAclId: "",
      identityProviders: [],
      userPoolDomainPrefix: "",
      publishedApiAllowedIpV4AddressRanges: [""],
      publishedApiAllowedIpV6AddressRanges: [""],
      allowedSignUpEmailDomains: [],
      autoJoinUserGroups: [],
      selfSignUpEnabled: true,
      enableIpV6: true,
      documentBucket: bedrockRegionResourcesStack.documentBucket,
      enableRagReplicas: false,
      enableBedrockGlobalInference: false,
      enableBedrockCrossRegionInference: false,
      allowedIpV4AddressRanges: [""],
      allowedIpV6AddressRanges: [""],
      enableLambdaSnapStart: true,
      alternateDomainName: "chat.example.com",
      hostedZoneId: "Z0123456789ABCDEF",
      enableBotStore: true,
      enableBotStoreReplicas: false,
      botStoreLanguage: "en",
      tokenValidMinutes: 60,
      alarmEmail: "",
      dailyChatCostAlarmUsd: 100,
      maxDedicatedKnowledgeBasesPerUser: 2,
      usageAnalysisRetentionDays: 90,
      apiThrottle: { rateLimit: 500, burstLimit: 1000 },
    });

    const template = Template.fromStack(customDomainStack);

    // Verify CloudFront distribution has alternate domain name
    template.hasResourceProperties("AWS::CloudFront::Distribution", {
      DistributionConfig: {
        Aliases: ["chat.example.com"],
      },
    });

    // Verify Route53 record is created
    template.hasResourceProperties("AWS::Route53::RecordSet", {
      Name: "chat.example.com.",
      Type: "A",
      AliasTarget: {
        DNSName: {
          "Fn::GetAtt": [Match.anyValue(), "DomainName"],
        },
        HostedZoneId: Match.anyValue(),
      },
      HostedZoneId: "Z0123456789ABCDEF",
    });

    // Verify AAAA record for IPv6
    template.hasResourceProperties("AWS::Route53::RecordSet", {
      Name: "chat.example.com.",
      Type: "AAAA",
      AliasTarget: {
        DNSName: {
          "Fn::GetAtt": [Match.anyValue(), "DomainName"],
        },
        HostedZoneId: Match.anyValue(),
      },
      HostedZoneId: "Z0123456789ABCDEF",
    });
  });

  test("no custom domain configuration", () => {
    const app = new cdk.App(testAppProps);

    const bedrockRegionResourcesStack = new BedrockRegionResourcesStack(
      app,
      "BedrockRegionResourcesStack",
      {
        env: {
          region: "us-east-1",
        },
        crossRegionReferences: true,
      }
    );

    const noDomainStack = new BedrockChatStack(app, "NoDomainStack", {
      env: {
        region: "us-east-1",
      },
      envName: "test",
      envPrefix: "test-",
      bedrockRegion: "us-east-1",
      crossRegionReferences: true,
      webAclId: "",
      identityProviders: [],
      userPoolDomainPrefix: "",
      publishedApiAllowedIpV4AddressRanges: [""],
      publishedApiAllowedIpV6AddressRanges: [""],
      allowedSignUpEmailDomains: [],
      autoJoinUserGroups: [],
      selfSignUpEnabled: true,
      enableIpV6: true,
      documentBucket: bedrockRegionResourcesStack.documentBucket,
      enableRagReplicas: false,
      enableBedrockGlobalInference: false,
      enableBedrockCrossRegionInference: false,
      enableLambdaSnapStart: true,
      alternateDomainName: "",
      allowedIpV4AddressRanges: [""],
      allowedIpV6AddressRanges: [""],
      hostedZoneId: "",
      enableBotStore: true,
      enableBotStoreReplicas: false,
      botStoreLanguage: "en",
      tokenValidMinutes: 60,
      alarmEmail: "",
      dailyChatCostAlarmUsd: 100,
      maxDedicatedKnowledgeBasesPerUser: 2,
      usageAnalysisRetentionDays: 90,
      apiThrottle: { rateLimit: 500, burstLimit: 1000 },
    });

    const template = Template.fromStack(noDomainStack);

    // Verify no Route53 records are created
    template.resourceCountIs("AWS::Route53::RecordSet", 0);

    // Verify no ACM certificate is created
    template.resourceCountIs("AWS::CertificateManager::Certificate", 0);

    // Verify CloudFront distribution has no aliases
    template.hasResourceProperties("AWS::CloudFront::Distribution", {
      DistributionConfig: {
        Aliases: Match.absent(),
      },
    });
  });

  test("Frontend WAF disabled => no WebACLId on CloudFront", () => {
    const app = new cdk.App(testAppProps);

    const bedrockRegionResourcesStack = new BedrockRegionResourcesStack(
      app,
      "BedrockRegionResourcesStackNoWaf",
      {
        env: { region: "us-east-1" },
        crossRegionReferences: true,
      }
    );

    const stack = new BedrockChatStack(app, "NoWafStack", {
      env: { region: "us-west-2" },
      envName: "test",
      envPrefix: "test-",
      bedrockRegion: "us-east-1",
      crossRegionReferences: true,
      // Simulate WAF disabled: no ARN provided from bin
      webAclId: "",
      identityProviders: [],
      userPoolDomainPrefix: "",
      publishedApiAllowedIpV4AddressRanges: [""],
      publishedApiAllowedIpV6AddressRanges: [""],
      allowedIpV4AddressRanges: [""],
      allowedIpV6AddressRanges: [""],
      allowedSignUpEmailDomains: [],
      autoJoinUserGroups: [],
      selfSignUpEnabled: true,
      enableIpV6: true,
      documentBucket: bedrockRegionResourcesStack.documentBucket,
      enableRagReplicas: false,
      enableBedrockGlobalInference: false,
      enableBedrockCrossRegionInference: false,
      enableLambdaSnapStart: true,
      enableBotStore: true,
      enableBotStoreReplicas: false,
      botStoreLanguage: "en",
      tokenValidMinutes: 60,
      alarmEmail: "",
      dailyChatCostAlarmUsd: 100,
      maxDedicatedKnowledgeBasesPerUser: 2,
      usageAnalysisRetentionDays: 90,
      apiThrottle: { rateLimit: 500, burstLimit: 1000 },
    });

    const template = Template.fromStack(stack);

    template.hasResourceProperties("AWS::CloudFront::Distribution", {
      DistributionConfig: {
        WebACLId: Match.absent(),
      },
    });
  });

  test("Frontend WAF enabled => WebACLId set on CloudFront", () => {
    const app = new cdk.App(testAppProps);

    const bedrockRegionResourcesStack = new BedrockRegionResourcesStack(
      app,
      "BedrockRegionResourcesStackWaf",
      {
        env: { region: "us-east-1" },
        crossRegionReferences: true,
      }
    );

    const wafArn = "arn:aws:wafv2:us-east-1:123456789012:global/webacl/test/uuid";

    const stack = new BedrockChatStack(app, "WithWafStack", {
      env: { region: "us-west-2" },
      envName: "test",
      envPrefix: "test-",
      bedrockRegion: "us-east-1",
      crossRegionReferences: true,
      webAclId: wafArn,
      identityProviders: [],
      userPoolDomainPrefix: "",
      publishedApiAllowedIpV4AddressRanges: [""],
      publishedApiAllowedIpV6AddressRanges: [""],
      allowedIpV4AddressRanges: [""],
      allowedIpV6AddressRanges: [""],
      allowedSignUpEmailDomains: [],
      autoJoinUserGroups: [],
      selfSignUpEnabled: true,
      enableIpV6: true,
      documentBucket: bedrockRegionResourcesStack.documentBucket,
      enableRagReplicas: false,
      enableBedrockGlobalInference: false,
      enableBedrockCrossRegionInference: false,
      enableLambdaSnapStart: true,
      enableBotStore: true,
      enableBotStoreReplicas: false,
      botStoreLanguage: "en",
      tokenValidMinutes: 60,
      alarmEmail: "",
      dailyChatCostAlarmUsd: 100,
      maxDedicatedKnowledgeBasesPerUser: 2,
      usageAnalysisRetentionDays: 90,
      apiThrottle: { rateLimit: 500, burstLimit: 1000 },
    });

    const template = Template.fromStack(stack);

    template.hasResourceProperties("AWS::CloudFront::Distribution", {
      DistributionConfig: {
        WebACLId: wafArn,
      },
    });
  });
});

describe("Bedrock Knowledge Base Stack", () => {
  const setupStack = (params: any = {}) => {
    const app = new cdk.App(testAppProps);

    const OWNER_USER_ID: string = "test-user-id";
    const BOT_ID: string = "test-bot-id";
    const KNOWLEDGE = {
      sitemap_urls: [],
      filenames: [
        "test-filename.pdf",
      ],
      source_urls: [
        "https://example.com",
      ],
      s3_urls: params.s3Urls !== undefined ? params.s3Urls : [],
    };

    const KNOWLEDGE_BASE = {
      type: "dedicated",
      chunking_strategy: "fixed_size",
      max_tokens: params.maxTokens,
      instruction: params.instruction,
      overlap_percentage: params.overlapPercentage,
      open_search: {
        analyzer:
          params.analyzer !== undefined
            ? JSON.parse(params.analyzer)
            : {
              character_filters: [
                "icu_normalizer",
              ],
              token_filters: [
                "kuromoji_baseform",
                "kuromoji_part_of_speech",
              ],
              tokenizer: "kuromoji_tokenizer",
            },
      },
      embeddings_model: "titan_v2",
    } as const;

    const BEDROCK_CLAUDE_CHAT_DOCUMENT_BUCKET_NAME =
      "test-document-bucket-name";

    const ownerUserId: string = OWNER_USER_ID;
    const botId: string = BOT_ID;
    const knowledgeBase = KNOWLEDGE_BASE;
    const knowledge = KNOWLEDGE;
    const existingS3Urls: string[] = knowledge.s3_urls;

    const knowledgeBaseType = getKnowledgeBaseType(knowledgeBase.type);
    const embeddingsModel = getEmbeddingModel(knowledgeBase.embeddings_model);
    const chunkingStrategy = getChunkingStrategy(
      knowledgeBase.chunking_strategy,
      knowledgeBase.embeddings_model,
      getChunkingOptions(knowledgeBase)
    );
    const instruction: string | undefined = knowledgeBase.instruction;
    const analyzer = knowledgeBase.open_search.analyzer
      ? getAnalyzer(knowledgeBase.open_search.analyzer)
      : undefined;

    const stack = new BedrockCustomBotStack(app, "BedrockCustomBotStackStack", {
      ownerUserId,
      botId,
      embeddingsModel,
      bedrockClaudeChatDocumentBucketName:
        BEDROCK_CLAUDE_CHAT_DOCUMENT_BUCKET_NAME,
      knowledgeBaseType,
      chunkingStrategy,
      existingS3Urls,
      instruction,
      analyzer,
      filenames: knowledge.filenames,
      sourceUrls: knowledge.source_urls,
      existKnowledgeBaseId: undefined,
    });

    return Template.fromStack(stack);
  };

  test("default kb stack", () => {
    const template = setupStack({
      s3Urls: [
        "s3://test-bucket/test-key",
      ],
      maxTokens: 500,
      instruction: "This is an example instruction.",
      overlapPercentage: 10,
      analyzer: `{
        "character_filters": [
          "icu_normalizer"
        ],
        "token_filters": [
          "kuromoji_baseform",
          "kuromoji_part_of_speech"
        ],
        "tokenizer": "kuromoji_tokenizer"
      }`,
    });
    expect(template).toBeDefined();
  });

  test("kb stack without maxTokens", () => {
    const template = setupStack({
      instruction: "This is an example instruction.",
      overlapPercentage: 10,
      analyzer: `{
        "character_filters": [
          "icu_normalizer"
        ],
        "token_filters": [
          "kuromoji_baseform",
          "kuromoji_part_of_speech"
        ],
        "tokenizer": "kuromoji_tokenizer"
      }`,
    });
    expect(template).toBeDefined();
  });

  test("kb stack without instruction", () => {
    const template = setupStack({
      maxTokens: 500,
      overlapPercentage: 10,
      analyzer: `{
        "character_filters": [
          "icu_normalizer"
        ],
        "token_filters": [
          "kuromoji_baseform",
          "kuromoji_part_of_speech"
        ],
        "tokenizer": "kuromoji_tokenizer"
      }`,
    });
    expect(template).toBeDefined();
  });

  test("kb stack without analyzer", () => {
    const template = setupStack({
      maxTokens: 500,
      instruction: "This is an example instruction.",
      overlapPercentage: 10,
    });
    expect(template).toBeDefined();
  });

  test("kb stack without overlapPercentage", () => {
    const template = setupStack({
      maxTokens: 500,
      instruction: "This is an example instruction.",
      analyzer: `{
        "character_filters": [
          "icu_normalizer"
        ],
        "token_filters": [
          "kuromoji_baseform",
          "kuromoji_part_of_speech"
        ],
        "tokenizer": "kuromoji_tokenizer"
      }`,
    });
    expect(template).toBeDefined();
  });
});

describe("Bedrock Shared Knowledge Bases Stack", () => {
  test("temporary files and logs expire", () => {
    const app = new cdk.App(testAppProps);
    const stack = new BedrockSharedKnowledgeBasesStack(
      app,
      "BrChatSharedKbStack",
      {
        env: { region: "us-east-1" },
        documentBucketName: "test-document-bucket-name",
        knowledgeBases: [
          {
            knowledgeBaseHash: "hash",
            embeddingsModel: getEmbeddingModel("titan_v2"),
            chunkingStrategy: getChunkingStrategy("default"),
          },
        ],
      }
    );
    const template = Template.fromStack(stack);

    template.hasResourceProperties("AWS::S3::Bucket", {
      LifecycleConfiguration: {
        Rules: [{ ExpirationInDays: 7, Status: "Enabled" }],
      },
    });
    template.hasResourceProperties("Custom::LogRetention", {
      RetentionInDays: 90,
    });
  });
});

describe("Api Publishment Stack", () => {
  test("queues deny requests without TLS", () => {
    const app = new cdk.App(testAppProps);
    const stack = new ApiPublishmentStack(app, "ApiPublishmentStackTest", {
      env: { region: "us-east-1" },
      bedrockRegion: "us-east-1",
      enableBedrockGlobalInference: false,
      enableBedrockCrossRegionInference: false,
      conversationTableName: "conversation-table",
      botTableName: "bot-table",
      tableAccessRoleArn: "arn:aws:iam::123456789012:role/table-access",
      webAclArn: "arn:aws:wafv2:us-east-1:123456789012:regional/webacl/test/id",
      largeMessageBucketName: "large-message-bucket",
      modelEnvironment: {},
      usagePlan: {},
      metricsNamespace: "BedrockChat",
      alarmTopicArn: "arn:aws:sns:us-east-1:123456789012:alarms",
    });
    const template = Template.fromStack(stack);

    // Answers that failed for good are reported through the chat stack's topic.
    template.hasResourceProperties("AWS::CloudWatch::Alarm", {
      MetricName: "ApproximateNumberOfMessagesVisible",
      AlarmActions: ["arn:aws:sns:us-east-1:123456789012:alarms"],
    });
    // Failures recorded for the client end the message normally, so they are
    // counted from the consumer's log as well.
    template.resourceCountIs("AWS::CloudWatch::Alarm", 2);
    template.hasResourceProperties("AWS::Logs::MetricFilter", {
      FilterPattern: '"Failed to answer message"',
    });
    template.hasResourceProperties("AWS::Lambda::Function", {
      Environment: {
        Variables: Match.objectLike({
          MAX_RECEIVE_COUNT: "2",
          METRICS_NAMESPACE: "BedrockChat",
        }),
      },
    });

    template.resourceCountIs("AWS::SQS::Queue", 2);
    const queuePolicies = Object.values(
      template.findResources("AWS::SQS::QueuePolicy")
    );
    expect(queuePolicies).toHaveLength(2);
    for (const policy of queuePolicies as any[]) {
      expect(policy.Properties.PolicyDocument.Statement).toContainEqual(
        expect.objectContaining({
          Effect: "Deny",
          Condition: { Bool: { "aws:SecureTransport": "false" } },
        })
      );
    }
  });
});
