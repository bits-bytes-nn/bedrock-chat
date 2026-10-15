import * as cdk from "aws-cdk-lib";
import * as fs from "fs";
import * as path from "path";
import {
  BedrockChatStack,
  BedrockChatStackProps,
} from "../lib/bedrock-chat-stack";
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

/** Policy statements attached to the role of a Lambda function in the template. */
const roleStatementsOf = (template: Template, fn: any): any[] => {
  const roleId = fn.Properties.Role["Fn::GetAtt"][0];
  return Object.values(template.findResources("AWS::IAM::Policy"))
    .filter((policy: any) =>
      policy.Properties.Roles.some((role: any) => role.Ref === roleId)
    )
    .flatMap((policy: any) => policy.Properties.PolicyDocument.Statement);
};
const actionsOf = (statements: any[]): string[] =>
  statements.flatMap((statement: any) => [statement.Action].flat());

/**
 * Checks that a function sends its logs to the log group of this ID prefix, kept
 * for 90 days, and that its role can write to the group.
 */
const expectFunctionLogsExpire = (template: Template, logGroupPrefix: string) => {
  const logGroups = Object.entries(
    template.findResources("AWS::Logs::LogGroup")
  ).filter(([id]) => id.startsWith(logGroupPrefix));
  expect(logGroups).toHaveLength(1);
  const [logGroupId, logGroup] = logGroups[0] as [string, any];
  expect(logGroup.Properties.RetentionInDays).toBe(90);
  const functions = Object.values(
    template.findResources("AWS::Lambda::Function", {
      Properties: { LoggingConfig: { LogGroup: { Ref: logGroupId } } },
    })
  );
  expect(functions).toHaveLength(1);
  const roleId = (functions[0] as any).Properties.Role["Fn::GetAtt"][0];
  const managedPolicies = JSON.stringify(
    template.findResources("AWS::IAM::Role")[roleId].Properties.ManagedPolicyArns ?? []
  );
  const writesToGroup = roleStatementsOf(template, functions[0]).some(
    (statement) =>
      [statement.Action].flat().includes("logs:PutLogEvents") &&
      JSON.stringify(statement.Resource).includes(logGroupId)
  );
  expect(
    managedPolicies.includes("AWSLambdaBasicExecutionRole") || writesToGroup
  ).toBe(true);
};

/** Chat stack with the settings of the default stack test, changed by `overrides`. */
const newChatStack = (
  overrides: Partial<BedrockChatStackProps> = {}
): Template => {
  const app = new cdk.App(testAppProps);
  const regionStack = new BedrockRegionResourcesStack(
    app,
    "BedrockRegionResourcesStack",
    { env: { region: "us-east-1" }, crossRegionReferences: true }
  );
  const stack = new BedrockChatStack(app, "MyTestStack", {
    env: { region: "us-west-2" },
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
    documentBucket: regionStack.documentBucket,
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
    ...overrides,
  });
  return Template.fromStack(stack);
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
    const logGroups = template.findResources("AWS::Logs::LogGroup");
    for (const project of deployProjects as any[]) {
      const groupName = project.Properties.LogsConfig.CloudWatchLogs.GroupName;
      expect(logGroups[groupName.Ref].Properties.RetentionInDays).toBe(90);
    }
    // The function logs expire as well.
    for (const id of [
      "WebSocketHandlerV2LogGroup",
      "BackendApiHandlerV2LogGroup",
      "EmbeddingSynchronizeDataSourceHandlerLogGroup",
      "EmbeddingBotRemovalHandlerLogGroup",
      "EmbeddingUpdateSyncStatusHandlerLogGroup",
      "SourceDeployLogGroup",
    ]) {
      expectFunctionLogsExpire(template, id);
    }

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
    // Roles that access the tables are created under a path that the table access
    // role trusts, because generated names shorten long stack names.
    const pathTrusted = Object.values(template.findResources("AWS::IAM::Role")).filter(
      (role: any) => role.Properties.Path === "/bedrock-chat/test-/"
    );
    expect(pathTrusted).toHaveLength(5);
    const tableTrust = JSON.stringify(
      Object.values(template.findResources("AWS::IAM::Role")).find((role: any) =>
        JSON.stringify(role.Properties.AssumeRolePolicyDocument).includes(
          "aws:PrincipalArn"
        )
      )
    );
    expect(tableTrust).toContain(":role/bedrock-chat/test-/*");
    expect(tableTrust).not.toContain("PrincipalTag");

    template.resourceCountIs("AWS::CloudWatch::Alarm", 11);
    template.hasResourceProperties("AWS::CloudWatch::Alarm", {
      MetricName: "BotUsageUpdateFailures",
      Period: 3600,
    });
    // The bot store's initial table exports hold conversation text, so they expire.
    template.hasResourceProperties("AWS::S3::Bucket", {
      LifecycleConfiguration: {
        Rules: [Match.objectLike({ ExpirationInDays: 7, Status: "Enabled" })],
      },
    });
    // The alarms read the namespace that the handlers publish to, which is per
    // environment (cdk/lib/utils/metrics.ts).
    const namespace = "BedrockChat/test-";
    template.hasResourceProperties("AWS::CloudWatch::Alarm", {
      Namespace: namespace,
      MetricName: "ChatCost",
      Statistic: "Sum",
      Period: 86400,
      Threshold: 100,
    });
    const handlerNamespaces = Object.values(
      template.findResources("AWS::Lambda::Function")
    ).flatMap((fn: any) => {
      const value = fn.Properties.Environment?.Variables?.METRICS_NAMESPACE;
      return value === undefined ? [] : [value];
    });
    // The REST API and chat handlers.
    expect(handlerNamespaces).toEqual([namespace, namespace]);
    // Connections are authorized when they open.
    template.hasResourceProperties("AWS::ApiGatewayV2::Route", {
      RouteKey: "$connect",
      AuthorizationType: "CUSTOM",
    });
    // The conversation list reads its index only (backend/app/repositories/conversation.py).
    const conversationTable = Object.values(
      template.findResources("AWS::DynamoDB::Table", {
        Properties: { StreamSpecification: Match.anyValue() },
      })
    ).find((table: any) =>
      (table.Properties.GlobalSecondaryIndexes ?? []).some(
        (index: any) => index.IndexName === "ConversationListIndex"
      )
    ) as any;
    const conversationIndexes = conversationTable.Properties.GlobalSecondaryIndexes;
    expect(conversationIndexes.map((index: any) => index.IndexName).sort()).toEqual([
      "ConversationListIndex",
      "SKIndex",
    ]);
    expect(
      conversationIndexes.find(
        (index: any) => index.IndexName === "ConversationListIndex"
      ).Projection
    ).toEqual({ ProjectionType: "INCLUDE", NonKeyAttributes: ["Title", "BotId"] });
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
    const logGroupIds = Object.keys(template.findResources("AWS::Logs::LogGroup"));
    for (const prefix of [
      "WebSocketHandlerV2LogGroup",
      "EmbeddingUpdateSyncStatusHandlerLogGroup",
    ]) {
      const logGroupId = logGroupIds.find((id) => id.startsWith(prefix));
      expect(logGroupId).toBeDefined();
      template.hasResourceProperties("AWS::Logs::MetricFilter", {
        LogGroupName: { Ref: logGroupId },
      });
    }
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

    // The shared knowledge bases stack is named per environment, and the build that
    // deploys it, the handler that reads it and the policy that allows it agree.
    const sharedStackName = "test--BrChatSharedKbStack";
    template.hasResourceProperties("AWS::Lambda::Function", {
      Environment: {
        Variables: Match.objectLike({
          SHARED_KNOWLEDGE_BASES_STACK_NAME: sharedStackName,
        }),
      },
    });
    template.hasResourceProperties("AWS::CodeBuild::Project", {
      Source: Match.objectLike({
        BuildSpec: Match.stringLikeRegexp(
          `deploy --require-approval never ${sharedStackName}"`
        ),
      }),
    });
    const describeStackResources = statements
      .filter((statement: any) => statement.Action === "cloudformation:DescribeStacks")
      .flatMap((statement: any) => [statement.Resource].flat());
    expect(JSON.stringify(describeStackResources)).toContain(
      `:stack/${sharedStackName}/*`
    );
    // Of the state machine handlers, only the sync status handler deletes stacks,
    // and only the knowledge base stacks of bots.
    const lambdaFunctions = Object.values(template.findResources("AWS::Lambda::Function"));
    const syncStatusHandler = lambdaFunctions.find((fn: any) =>
      JSON.stringify(fn.Properties.ImageConfig ?? {}).includes(".update_bot_status.")
    );
    const deleteStackResources = roleStatementsOf(template, syncStatusHandler)
      .filter((statement: any) => statement.Action === "cloudformation:DeleteStack")
      .flatMap((statement: any) => [statement.Resource].flat());
    expect(JSON.stringify(deleteStackResources)).toContain("stack/BrChatKbStack*/*");
    expect(JSON.stringify(deleteStackResources)).not.toContain(sharedStackName);
    const ingestionHandler = lambdaFunctions.find((fn: any) =>
      JSON.stringify(fn.Properties.ImageConfig ?? {}).includes(
        ".synchronize_data_source."
      )
    );
    expect(actionsOf(roleStatementsOf(template, ingestionHandler))).not.toContain(
      "cloudformation:DeleteStack"
    );

    // The API handler starts the API publication build only. Knowledge base builds
    // are started by the state machine.
    const functions = template.findResources("AWS::Lambda::Function");
    const apiHandler = Object.values(functions).find(
      (fn: any) =>
        fn.Properties.Environment?.Variables?.PUBLISH_API_CODEBUILD_PROJECT_NAME
    );
    const apiHandlerStatements = roleStatementsOf(template, apiHandler);
    const codebuildStatements = apiHandlerStatements.filter((statement: any) =>
      [statement.Action].flat().includes("codebuild:StartBuild")
    );
    expect(codebuildStatements).toHaveLength(1);
    expect([codebuildStatements[0].Resource].flat()).toHaveLength(1);
    // It only starts executions of the embedding state machine.
    const sfnStatements = apiHandlerStatements.filter((statement: any) =>
      [statement.Action].flat().some((action: string) => action.startsWith("states:"))
    );
    expect(
      sfnStatements.map((statement: any) => [statement.Action].flat()).flat().sort()
    ).toEqual(["states:StartExecution"]);
    expect(JSON.stringify(sfnStatements)).not.toContain('"*"');
    // DescribeIndex and ReadDocument are data access policy permissions, not IAM actions.
    expect(actions).not.toContain("aoss:DescribeIndex");
    expect(actions).not.toContain("aoss:ReadDocument");

    // The ingestion pipelines write to the bot store collection only, and do not
    // need OpenSearch Service domain actions.
    expect(actions.some((action) => action.startsWith("es:"))).toBe(false);
    const collectionId = Object.keys(
      template.findResources("AWS::OpenSearchServerless::Collection")
    )[0];
    const apiAccessStatements = statements.filter((statement: any) =>
      [statement.Action].flat().includes("aoss:APIAccessAll")
    );
    // The API handler and the pipelines.
    expect(apiAccessStatements).toHaveLength(2);
    for (const statement of apiAccessStatements) {
      expect(statement.Resource).toEqual({ "Fn::GetAtt": [collectionId, "Arn"] });
    }

    // Bot stacks are looked up in the Region that they are deployed to.
    const stackArns = JSON.stringify(
      statements
        .filter((statement: any) =>
          [statement.Action].flat().includes("cloudformation:DeleteStack")
        )
        .map((statement: any) => statement.Resource)
    );
    expect(stackArns).not.toContain(":cloudformation:*:");
    expect(stackArns).toContain(":cloudformation:us-east-1:");
    expect(stackArns).toContain("stack/ApiPublishmentStack*/*");
    expect(stackArns).toContain("stack/BrChatKbStack*/*");
    expect(JSON.stringify(statements)).not.toContain(":logs:*:*:*");

    // Only the Lambda roles of this stack and of published API stacks can assume
    // the table access role. CloudFormation names roles after their stack.
    for (const role of Object.values(
      template.findResources("AWS::IAM::Role")
    ) as any[]) {
      expect(role.Properties.RoleName).toBeUndefined();
    }
    const tableAccessRole = Object.entries(
      template.findResources("AWS::IAM::Role")
    ).find(([id]) => id.startsWith("DatabaseTableAccessRole"))![1] as any;
    const trust = JSON.stringify(
      tableAccessRole.Properties.AssumeRolePolicyDocument
    );
    expect(trust).toContain('"ArnLike":{"aws:PrincipalArn"');
    expect(trust).toContain(":role/MyTestStack-*");
    expect(trust).toContain(":role/ApiPublishmentStack*");

    // Knowledge syncs end within a day and alarm when they fail, time out or are
    // aborted. A bot is marked ready a minute after its ingestion, and a failed
    // update of that status marks it failed instead of leaving it RUNNING.
    const stateMachine = Object.values(
      template.findResources("AWS::StepFunctions::StateMachine")
    )[0] as any;
    const definition = JSON.parse(
      stateMachine.Properties.DefinitionString["Fn::Join"][1]
        .map((part: any) => (typeof part === "string" ? part : "TOKEN"))
        .join("")
    );
    expect(definition.TimeoutSeconds).toBe(86400);
    const mapQueuedBots = definition.States.MapQueuedBots.ItemProcessor.States;
    expect(mapQueuedBots.WaitForSearchIndex).toMatchObject({
      Type: "Wait",
      Seconds: 60,
      Next: "UpdateSyncStatusSuccess",
    });
    expect(mapQueuedBots.UpdateSyncStatusSuccess.Catch).toEqual([
      expect.objectContaining({ Next: "UpdateSyncStatusFailedForCustomBot" }),
    ]);
    const syncAlarm = Object.values(
      template.findResources("AWS::CloudWatch::Alarm", {
        Properties: { AlarmDescription: Match.stringLikeRegexp("timed out") },
      })
    )[0] as any;
    expect(
      syncAlarm.Properties.Metrics.flatMap((metric: any) =>
        metric.MetricStat ? [metric.MetricStat.Metric.MetricName] : []
      )
    ).toEqual(["ExecutionsFailed", "ExecutionsTimedOut", "ExecutionsAborted"]);
    expect(syncAlarm.Properties.Metrics).toContainEqual(
      expect.objectContaining({ Expression: "failed + timedOut + aborted" })
    );

    // The usage export runs from a schedule, so its failures alarm on Lambda errors.
    const exportHandlerId = Object.entries(functions).find(
      ([, fn]: [string, any]) =>
        fn.Properties.Environment?.Variables?.BUCKET_NAME &&
        fn.Properties.Environment?.Variables?.TABLE_ARN
    )![0];
    template.hasResourceProperties("AWS::CloudWatch::Alarm", {
      Namespace: "AWS/Lambda",
      MetricName: "Errors",
      Dimensions: [{ Name: "FunctionName", Value: { Ref: exportHandlerId } }],
    });
    // Longer than the 3 second default, for a cold start and SDK retries.
    expect((functions[exportHandlerId] as any).Properties.Timeout).toBe(30);

    // The state machine catches the sync status handler's errors, so they alarm.
    const [syncStatusHandlerId] = Object.entries(functions).find(([, fn]: [string, any]) =>
      JSON.stringify(fn.Properties.ImageConfig?.Command ?? []).includes(
        "update_bot_status.handler"
      )
    )!;
    template.hasResourceProperties("AWS::CloudWatch::Alarm", {
      Namespace: "AWS/Lambda",
      MetricName: "Errors",
      Threshold: 1,
      Dimensions: [{ Name: "FunctionName", Value: { Ref: syncStatusHandlerId } }],
    });

    // Bot removals have the memory of the other backend handlers, and a stuck
    // record goes to the dead-letter queue before the stream drops it.
    const removalHandler = Object.values(functions).find((fn: any) =>
      JSON.stringify(fn.Properties.ImageConfig ?? {}).includes("app.bot_remove")
    ) as any;
    expect(removalHandler.Properties.MemorySize).toBe(512);
    template.hasResourceProperties("AWS::Lambda::EventSourceMapping", {
      MaximumRecordAgeInSeconds: 12 * 3600,
      DestinationConfig: Match.objectLike({ OnFailure: Match.anyValue() }),
    });
    // The document bucket is an output of the Bedrock Region stack only.
    expect(Object.keys(template.toJSON().Outputs)).not.toContain(
      "DocumentBucketName"
    );
    expect(Object.keys(regionTemplate.toJSON().Outputs)).toContain(
      "DocumentBucketName"
    );
    // The lock handler reads the bucket and the Bedrock Region only.
    const lockHandler = Object.values(functions).find((fn: any) =>
      JSON.stringify(fn.Properties.ImageConfig ?? {}).includes(".lock.handler")
    ) as any;
    expect(Object.keys(lockHandler.Properties.Environment.Variables).sort()).toEqual(
      ["BEDROCK_REGION", "DOCUMENT_BUCKET"]
    );
  });

  test("usage exports expire after the retention days", () => {
    // Exports hold conversation text, including deleted conversations.
    const template = newChatStack({ usageAnalysisRetentionDays: 30 });

    const expiringBuckets = template.findResources("AWS::S3::Bucket", {
      Properties: {
        LifecycleConfiguration: {
          Rules: [Match.objectLike({ ExpirationInDays: 30, Status: "Enabled" })],
        },
      },
    });
    // The table exports and the Athena query results.
    expect(Object.keys(expiringBuckets)).toHaveLength(2);
  });

  test("auto-joined user groups register the Cognito triggers", () => {
    const template = newChatStack({ autoJoinUserGroups: ["Users"] });

    // Registered again on every deployment, because CloudFormation's user pool
    // updates reset the triggers.
    template.hasResourceProperties("Custom::CognitoTrigger", {
      Triggers: {
        PostConfirmation: Match.anyValue(),
        PostAuthentication: Match.anyValue(),
      },
      DeployedAt: Match.anyValue(),
    });
    const actions = actionsOf(
      Object.values(template.findResources("AWS::IAM::Policy")).flatMap(
        (policy: any) => policy.Properties.PolicyDocument.Statement
      )
    );
    expect(actions).toContain("cognito-idp:UpdateUserPool");
    expect(actions).toContain("cognito-idp:AdminAddUserToGroup");

    // The registration function's logs expire as well.
    expectFunctionLogsExpire(
      template,
      "AuthCognitoTriggerRegistrationFunctionLogGroup"
    );
  });

  test("the Cognito trigger code fits in an inline CloudFormation function", () => {
    // CloudFormation accepts at most 4096 bytes of ZipFile code.
    const code = fs.readFileSync(
      path.join(__dirname, "../custom-resources/cognito-trigger/index.py")
    );
    expect(code.byteLength).toBeLessThan(4096);
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
    expectFunctionLogsExpire(template, "KnowledgeBasehashTransformationFunctionLogGroup");
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
      tableAccessRolePath: "/bedrock-chat/default/",
    });
    const template = Template.fromStack(stack);

    // Both handler roles assume the chat stack's table access role, which trusts
    // roles under this path.
    const pathRoles = Object.values(template.findResources("AWS::IAM::Role")).filter(
      (role: any) => role.Properties.Path === "/bedrock-chat/default/"
    );
    expect(pathRoles).toHaveLength(2);

    // Answers that failed for good are reported through the chat stack's topic.
    template.hasResourceProperties("AWS::CloudWatch::Alarm", {
      MetricName: "ApproximateNumberOfMessagesVisible",
      AlarmActions: ["arn:aws:sns:us-east-1:123456789012:alarms"],
    });
    // Failures recorded for the client end the message normally, so the consumer
    // publishes them as a metric of this API. Both handlers alarm on Lambda errors.
    template.resourceCountIs("AWS::CloudWatch::Alarm", 4);
    template.resourceCountIs("AWS::Logs::MetricFilter", 0);
    template.hasResourceProperties("AWS::CloudWatch::Alarm", {
      Namespace: "BedrockChat",
      MetricName: "FailedAnswers",
      Dimensions: [{ Name: "PublishedApiId", Value: "Test" }],
      Statistic: "Sum",
      AlarmActions: ["arn:aws:sns:us-east-1:123456789012:alarms"],
    });
    const errorAlarms = template.findResources("AWS::CloudWatch::Alarm", {
      Properties: { Namespace: "AWS/Lambda", MetricName: "Errors" },
    });
    expect(Object.keys(errorAlarms)).toHaveLength(2);
    for (const alarm of Object.values(errorAlarms) as any[]) {
      expect(alarm.Properties.AlarmActions).toEqual([
        "arn:aws:sns:us-east-1:123456789012:alarms",
      ]);
    }

    const functions = template.findResources("AWS::Lambda::Function");
    const consumer = Object.values(functions).find(
      (fn: any) => fn.Properties.Environment?.Variables?.MAX_RECEIVE_COUNT
    ) as any;
    const apiHandler = Object.values(functions).find(
      (fn: any) => fn.Properties.Environment?.Variables?.CORS_ALLOW_ORIGINS
    ) as any;
    // The consumer reads the API ID for the metric dimension and the queue to retry
    // messages soon, not CORS.
    expect(consumer.Properties.Environment.Variables).toMatchObject({
      MAX_RECEIVE_COUNT: "2",
      METRICS_NAMESPACE: "BedrockChat",
      PUBLISHED_API_ID: "Test",
      QUEUE_URL: expect.anything(),
    });
    expect(consumer.Properties.Environment.Variables).not.toHaveProperty(
      "CORS_ALLOW_ORIGINS"
    );

    // The API handler only queues messages and reads conversations, so its role
    // cannot call models.
    const roleActions = (fn: any) => actionsOf(roleStatementsOf(template, fn));
    expect(apiHandler.Properties.Role).not.toEqual(consumer.Properties.Role);
    const apiActions = roleActions(apiHandler);
    expect(apiActions).toContain("sqs:SendMessage");
    expect(apiActions).toContain("sts:AssumeRole");
    expect(apiActions.some((action) => action.startsWith("bedrock:"))).toBe(false);
    expect(apiActions).not.toContain("s3:PutObject");
    expect(roleActions(consumer)).toContain("bedrock:InvokeModelWithResponseStream");
    expect(roleActions(consumer)).toContain("sqs:ChangeMessageVisibility");

    // Concurrent answers are bounded, and a message stays invisible for six times
    // the consumer timeout.
    // The consumer reports messages to retry instead of failing the invocation.
    template.hasResourceProperties("AWS::Lambda::EventSourceMapping", {
      BatchSize: 1,
      ScalingConfig: { MaximumConcurrency: 10 },
      FunctionResponseTypes: ["ReportBatchItemFailures"],
    });
    expect(consumer.Properties.Timeout).toBe(900);
    // The API checks messages against the queue's maximum size before sending them.
    template.hasResourceProperties("AWS::SQS::Queue", {
      VisibilityTimeout: 900 * 6,
      MaximumMessageSize: 1024 * 1024,
    });
    template.hasResourceProperties("AWS::Lambda::Function", {
      Environment: {
        Variables: Match.objectLike({ QUEUE_MAX_MESSAGE_BYTES: String(1024 * 1024) }),
      },
    });

    // The WAF association names the stage, so it waits for the stage.
    const stageId = Object.keys(template.findResources("AWS::ApiGateway::Stage"))[0];
    const association = Object.values(
      template.findResources("AWS::WAFv2::WebACLAssociation")
    )[0] as any;
    expect(association.DependsOn).toContain(stageId);

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
