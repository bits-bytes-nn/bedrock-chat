import { Construct } from "constructs";
import { CfnOutput, CfnResource, Duration } from "aws-cdk-lib";
import { HttpLambdaIntegration } from "aws-cdk-lib/aws-apigatewayv2-integrations";
import { HttpUserPoolAuthorizer } from "aws-cdk-lib/aws-apigatewayv2-authorizers";
import {
  Architecture,
  IFunction,
  LayerVersion,
  Runtime,
  SnapStartConf,
} from "aws-cdk-lib/aws-lambda";
import {
  CorsHttpMethod,
  HttpApi,
  HttpMethod,
} from "aws-cdk-lib/aws-apigatewayv2";
import { Auth } from "./auth";
import { Stack } from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";

// Transcription jobs started by the API, which IAM is scoped to.
const TRANSCRIPTION_JOB_PREFIX = "brchat-";
// Runs FastAPI on Lambda. The layer is published in the commercial partition only.
// https://github.com/awslabs/aws-lambda-web-adapter?tab=readme-ov-file#lambda-functions-packaged-as-zip-package-for-aws-managed-runtimes
const lambdaWebAdapterLayerArn = (region: string) =>
  `arn:aws:lambda:${region}:753240598075:layer:LambdaAdapterLayerX86:23`;
import {
  botStackPolicyStatement,
  publishedApiKeyPolicyStatement,
} from "../utils/publication-policies";
import { apiPublishmentStackPrefix } from "../utils/stack-names";
import * as logs from "aws-cdk-lib/aws-logs";
import * as path from "path";
import { IBucket } from "aws-cdk-lib/aws-s3";
import * as codebuild from "aws-cdk-lib/aws-codebuild";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import { UsageAnalysis } from "./usage-analysis";
import { excludeDockerImage, POETRY_VERSION } from "../constants/docker";
import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";
import { Database } from "./database";
import {
  bedrockChatPolicyStatement,
  firecrawlSecretPolicyStatement,
} from "../utils/bedrock-policies";
import { CfnStage, ThrottleSettings } from "aws-cdk-lib/aws-apigatewayv2";
import { lambdaLogGroup } from "../utils/lambda-log-group";

export interface ApiProps {
  readonly database: Database;
  readonly envName: string;
  readonly envPrefix: string;
  readonly corsAllowOrigins: string[];
  readonly throttle: ThrottleSettings;
  readonly auth: Auth;
  readonly bedrockRegion: string;
  readonly documentBucket: IBucket;
  readonly largeMessageBucket: IBucket;
  readonly apiPublishProject: codebuild.IProject;
  readonly embeddingStateMachine: sfn.IStateMachine;
  readonly usageAnalysis: UsageAnalysis;
  readonly enableBedrockGlobalInference: boolean;
  readonly enableBedrockCrossRegionInference: boolean;
  readonly enableLambdaSnapStart: boolean;
  readonly openSearchEndpoint?: string;
  /** Bot store collection that the handler searches, if the bot store is enabled. */
  readonly openSearchCollectionArn?: string;
  readonly globalAvailableModels?: string[];
  readonly defaultModel?: string;
  readonly titleModel?: string;
  readonly maxDedicatedKnowledgeBasesPerUser: number;
  readonly metricsNamespace: string;
  readonly logoPath?: string;
}

export class Api extends Construct {
  readonly api: HttpApi;
  readonly handler: IFunction;
  constructor(scope: Construct, id: string, props: ApiProps) {
    super(scope, id);

    const { database, corsAllowOrigins: allowOrigins } = props;
    const { tableAccessRole } = database;

    const { usageAnalysis } = props;

    const handlerRole = new iam.Role(this, "HandlerRole", {
      path: props.database.tableAccessRolePath,
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
    });
    handlerRole.addManagedPolicy(
      iam.ManagedPolicy.fromAwsManagedPolicyName(
        "service-role/AWSLambdaBasicExecutionRole"
      )
    );
    handlerRole.addToPolicy(
      // Assume the table access role for row-level access control.
      new iam.PolicyStatement({
        actions: ["sts:AssumeRole"],
        resources: [tableAccessRole.roleArn],
      })
    );
    handlerRole.addToPolicy(bedrockChatPolicyStatement());
    handlerRole.addToPolicy(
      // Publishes APIs. Knowledge base builds are started by the embedding state machine.
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ["codebuild:StartBuild", "codebuild:BatchGetBuilds"],
        resources: [props.apiPublishProject.projectArn],
      })
    );
    props.embeddingStateMachine.grantStartExecution(handlerRole);
    handlerRole.addToPolicy(
      botStackPolicyStatement(Stack.of(this), [
        { stackNamePrefix: apiPublishmentStackPrefix, region: Stack.of(this).region },
      ])
    );
    handlerRole.addToPolicy(publishedApiKeyPolicyStatement(Stack.of(this)));
    handlerRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          "athena:GetWorkGroup",
          "athena:StartQueryExecution",
          "athena:StopQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:GetDataCatalog",
        ],
        resources: [usageAnalysis.workgroupArn],
      })
    );
    handlerRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          "glue:GetDatabase",
          "glue:GetDatabases",
          "glue:GetTable",
          "glue:GetTables",
          "glue:GetPartition",
          "glue:GetPartitions",
        ],
        resources: [
          usageAnalysis.database.databaseArn,
          usageAnalysis.database.catalogArn,
          usageAnalysis.ddbExportTable.tableArn,
        ],
      })
    );
    handlerRole.addToPolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: [
          "cognito-idp:AdminGetUser",
          "cognito-idp:ListUsers",
          "cognito-idp:ListGroups",
        ],
        resources: [props.auth.userPool.userPoolArn],
      })
    );
    if (props.openSearchCollectionArn) {
      // Bot store search. The handler calls the collection endpoint only.
      handlerRole.addToPolicy(
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: ["aoss:APIAccessAll"],
          resources: [props.openSearchCollectionArn],
        })
      );
    }
    // Bots with the internet search tool keep their Firecrawl API key here.
    // CreateSecret sets a tag, which needs TagResource.
    handlerRole.addToPolicy(
      firecrawlSecretPolicyStatement(Stack.of(this), [
        "secretsmanager:CreateSecret",
        "secretsmanager:UpdateSecret",
        "secretsmanager:GetSecretValue",
        "secretsmanager:DeleteSecret",
        "secretsmanager:TagResource",
      ])
    );
    usageAnalysis.resultOutputBucket.grantReadWrite(handlerRole);
    usageAnalysis.ddbBucket.grantRead(handlerRole);
    props.largeMessageBucket.grantReadWrite(handlerRole);
    handlerRole.addToPolicy(
      // Transcribes recordings in the document bucket, which is in the Bedrock Region.
      // Transcribe reads and writes the bucket with the caller's permissions.
      new iam.PolicyStatement({
        actions: [
          "transcribe:StartTranscriptionJob",
          "transcribe:GetTranscriptionJob",
        ],
        resources: [
          `arn:${Stack.of(this).partition}:transcribe:${props.bedrockRegion}:${
            Stack.of(this).account
          }:transcription-job/${TRANSCRIPTION_JOB_PREFIX}*`,
        ],
      })
    );

    const handler = new PythonFunction(this, "HandlerV2", {
      entry: path.join(__dirname, "../../../backend"),
      index: "app/main.py",
      bundling: {
        assetExcludes: [...excludeDockerImage],
        buildArgs: { POETRY_VERSION },
      },
      runtime: Runtime.PYTHON_3_13,
      architecture: Architecture.X86_64,
      memorySize: 1024,
      // API Gateway ends the request after 30 seconds, so a longer run is wasted.
      timeout: Duration.seconds(30),
      environment: {
        CONVERSATION_TABLE_NAME: database.conversationTable.tableName,
        BOT_TABLE_NAME: database.botTable.tableName,
        ENV_NAME: props.envName,
        ENV_PREFIX: props.envPrefix,
        CORS_ALLOW_ORIGINS: allowOrigins.join(","),
        USER_POOL_ID: props.auth.userPool.userPoolId,
        CLIENT_ID: props.auth.client.userPoolClientId,
        ACCOUNT: Stack.of(this).account,
        REGION: Stack.of(this).region,
        BEDROCK_REGION: props.bedrockRegion,
        TABLE_ACCESS_ROLE_ARN: tableAccessRole.roleArn,
        DOCUMENT_BUCKET: props.documentBucket.bucketName,
        LARGE_MESSAGE_BUCKET: props.largeMessageBucket.bucketName,
        PUBLISH_API_CODEBUILD_PROJECT_NAME: props.apiPublishProject.projectName,
        EMBEDDING_STATE_MACHINE_ARN: props.embeddingStateMachine.stateMachineArn,
        USAGE_ANALYSIS_DATABASE: usageAnalysis.database.databaseName,
        USAGE_ANALYSIS_TABLE: usageAnalysis.ddbExportTable.tableName,
        USAGE_ANALYSIS_WORKGROUP: usageAnalysis.workgroupName,
        USAGE_ANALYSIS_OUTPUT_LOCATION: `s3://${usageAnalysis.resultOutputBucket.bucketName}`,
        TRANSCRIPTION_JOB_PREFIX,
        ENABLE_BEDROCK_GLOBAL_INFERENCE:
          props.enableBedrockGlobalInference.toString(),
        ENABLE_BEDROCK_CROSS_REGION_INFERENCE:
          props.enableBedrockCrossRegionInference.toString(),
        GLOBAL_AVAILABLE_MODELS: props.globalAvailableModels 
          ? JSON.stringify(props.globalAvailableModels)
          : "[]",
        DEFAULT_MODEL: props.defaultModel || "",
        TITLE_MODEL: props.titleModel || "",
        MAX_DEDICATED_KNOWLEDGE_BASES_PER_USER:
          props.maxDedicatedKnowledgeBasesPerUser.toString(),
        METRICS_NAMESPACE: props.metricsNamespace,
        OPENSEARCH_DOMAIN_ENDPOINT: props.openSearchEndpoint || "",
        LOGO_PATH: props.logoPath || "",
        AWS_LAMBDA_EXEC_WRAPPER: "/opt/bootstrap",
        PORT: "8000",
      },
      role: handlerRole,
      logGroup: lambdaLogGroup(this, "HandlerV2LogGroup"),
      snapStart: props.enableLambdaSnapStart
        ? SnapStartConf.ON_PUBLISHED_VERSIONS
        : undefined,
      layers: [
        LayerVersion.fromLayerVersionArn(
          this,
          "LwaLayer",
          lambdaWebAdapterLayerArn(Stack.of(this).region)
        ),
      ],
    });
    // https://github.com/awslabs/aws-lambda-web-adapter/tree/main/examples/fastapi-zip
    (handler.node.defaultChild as CfnResource).addPropertyOverride(
      "Handler",
      "run.sh"
    );

    const api = new HttpApi(this, "Default", {
      description: `Main API for ${Stack.of(this).stackName}`,
      corsPreflight: {
        allowHeaders: ["*"],
        allowMethods: [
          CorsHttpMethod.GET,
          CorsHttpMethod.HEAD,
          CorsHttpMethod.OPTIONS,
          CorsHttpMethod.POST,
          CorsHttpMethod.PUT,
          CorsHttpMethod.PATCH,
          CorsHttpMethod.DELETE,
        ],
        allowOrigins: allowOrigins,
        maxAge: Duration.days(10),
      },
    });
    const defaultStage = api.defaultStage?.node.defaultChild as CfnStage;
    defaultStage.defaultRouteSettings = {
      throttlingRateLimit: props.throttle.rateLimit,
      throttlingBurstLimit: props.throttle.burstLimit,
    };
    const accessLogGroup = new logs.LogGroup(this, "AccessLogs", {
      retention: logs.RetentionDays.THREE_MONTHS,
    });
    defaultStage.accessLogSettings = {
      destinationArn: accessLogGroup.logGroupArn,
      format: JSON.stringify({
        requestId: "$context.requestId",
        ip: "$context.identity.sourceIp",
        requestTime: "$context.requestTime",
        routeKey: "$context.routeKey",
        status: "$context.status",
        responseLength: "$context.responseLength",
        integrationLatency: "$context.integrationLatency",
        integrationError: "$context.integrationErrorMessage",
      }),
    };

    const integration = new HttpLambdaIntegration(
      "Integration",
      handler.currentVersion
    );
    const authorizer = new HttpUserPoolAuthorizer(
      "Authorizer",
      props.auth.userPool,
      {
        userPoolClients: [props.auth.client],
      }
    );
    let routeProps: any = {
      path: "/{proxy+}",
      integration,
      methods: [
        HttpMethod.GET,
        HttpMethod.POST,
        HttpMethod.PUT,
        HttpMethod.PATCH,
        HttpMethod.DELETE,
      ],
      authorizer,
    };

    api.addRoutes(routeProps);

    this.api = api;
    this.handler = handler;

    new CfnOutput(this, "BackendApiUrl", { value: api.apiEndpoint });
  }
}
