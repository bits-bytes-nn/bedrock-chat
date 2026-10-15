import { Construct } from "constructs";
import * as apigwv2 from "aws-cdk-lib/aws-apigatewayv2";
import { WebSocketLambdaIntegration } from "aws-cdk-lib/aws-apigatewayv2-integrations";
import { WebSocketLambdaAuthorizer } from "aws-cdk-lib/aws-apigatewayv2-authorizers";

import { IFunction, Runtime, SnapStartConf } from "aws-cdk-lib/aws-lambda";
import * as path from "path";
import * as iam from "aws-cdk-lib/aws-iam";
import { CfnOutput, Duration, Stack } from "aws-cdk-lib";
import { Auth } from "./auth";
import { CfnRouteResponse } from "aws-cdk-lib/aws-apigatewayv2";
import * as logs from "aws-cdk-lib/aws-logs";
import * as s3 from "aws-cdk-lib/aws-s3";
import { excludeDockerImage, POETRY_VERSION } from "../constants/docker";
import { PythonFunction } from "@aws-cdk/aws-lambda-python-alpha";
import { Database } from "./database";
import {
  bedrockChatPolicyStatement,
  firecrawlSecretPolicyStatement,
} from "../utils/bedrock-policies";
import { lambdaLogGroup } from "../utils/lambda-log-group";

export interface WebSocketProps {
  readonly database: Database;
  readonly auth: Auth;
  readonly bedrockRegion: string;
  readonly documentBucket: s3.IBucket;
  readonly largeMessageBucket: s3.IBucket;
  readonly enableBedrockGlobalInference: boolean;
  readonly enableBedrockCrossRegionInference: boolean;
  readonly enableLambdaSnapStart: boolean;
  readonly globalAvailableModels?: string[];
  readonly defaultModel?: string;
  readonly titleModel?: string;
  readonly throttle: apigwv2.ThrottleSettings;
  readonly metricsNamespace: string;
}

export class WebSocket extends Construct {
  readonly webSocketApi: apigwv2.IWebSocketApi;
  readonly handler: IFunction;
  readonly handlerLogGroup: logs.ILogGroup;
  private readonly defaultStageName = "dev";

  constructor(scope: Construct, id: string, props: WebSocketProps) {
    super(scope, id);

    const { database } = props;
    const { tableAccessRole } = database;

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

    // Bots with the internet search tool keep their Firecrawl API key here.
    handlerRole.addToPolicy(
      firecrawlSecretPolicyStatement(Stack.of(this), [
        "secretsmanager:GetSecretValue",
      ])
    );

    database.websocketSessionTable.grantReadWriteData(handlerRole);
    props.largeMessageBucket.grantReadWrite(handlerRole);
    props.documentBucket.grantRead(handlerRole);

    const handler = new PythonFunction(this, "HandlerV2", {
      entry: path.join(__dirname, "../../../backend"),
      index: "app/websocket.py",
      bundling: {
        assetExcludes: [...excludeDockerImage],
        buildArgs: { POETRY_VERSION },
      },
      runtime: Runtime.PYTHON_3_13,
      memorySize: 512,
      timeout: Duration.minutes(15),
      environment: {
        ACCOUNT: Stack.of(this).account,
        REGION: Stack.of(this).region,
        USER_POOL_ID: props.auth.userPool.userPoolId,
        CLIENT_ID: props.auth.client.userPoolClientId,
        BEDROCK_REGION: props.bedrockRegion,
        CONVERSATION_TABLE_NAME: database.conversationTable.tableName,
        BOT_TABLE_NAME: database.botTable.tableName,
        TABLE_ACCESS_ROLE_ARN: tableAccessRole.roleArn,
        LARGE_MESSAGE_BUCKET: props.largeMessageBucket.bucketName,
        WEBSOCKET_SESSION_TABLE_NAME: database.websocketSessionTable.tableName,
        ENABLE_BEDROCK_GLOBAL_INFERENCE:
          props.enableBedrockGlobalInference.toString(),
        ENABLE_BEDROCK_CROSS_REGION_INFERENCE:
          props.enableBedrockCrossRegionInference.toString(),
        // Model allowlist enforced on chat, and the model for search summaries.
        GLOBAL_AVAILABLE_MODELS: JSON.stringify(props.globalAvailableModels ?? []),
        DEFAULT_MODEL: props.defaultModel || "",
        TITLE_MODEL: props.titleModel || "",
        METRICS_NAMESPACE: props.metricsNamespace,
      },
      role: handlerRole,
      snapStart: props.enableLambdaSnapStart
        ? SnapStartConf.ON_PUBLISHED_VERSIONS
        : undefined,
      logGroup: lambdaLogGroup(this, "HandlerV2LogGroup"),
    });

    // Rejects connections without a valid ID token. Browsers cannot set headers on
    // a WebSocket, so the token comes in the query string.
    const authorizerHandler = new PythonFunction(this, "ConnectAuthorizer", {
      entry: path.join(__dirname, "../../../backend"),
      index: "app/websocket_authorizer.py",
      bundling: {
        assetExcludes: [...excludeDockerImage],
        buildArgs: { POETRY_VERSION },
      },
      runtime: Runtime.PYTHON_3_13,
      memorySize: 256,
      timeout: Duration.seconds(10),
      environment: {
        REGION: Stack.of(this).region,
        USER_POOL_ID: props.auth.userPool.userPoolId,
        CLIENT_ID: props.auth.client.userPoolClientId,
      },
      logGroup: lambdaLogGroup(this, "ConnectAuthorizerLogGroup"),
    });

    const webSocketApi = new apigwv2.WebSocketApi(this, "WebSocketApi", {
      connectRouteOptions: {
        integration: new WebSocketLambdaIntegration(
          "ConnectIntegration",
          handler.currentVersion
        ),
        authorizer: new WebSocketLambdaAuthorizer(
          "ConnectAuthorizer",
          authorizerHandler,
          { identitySource: ["route.request.querystring.token"] }
        ),
      },
    });
    const route = webSocketApi.addRoute("$default", {
      integration: new WebSocketLambdaIntegration(
        "DefaultIntegration",
        handler.currentVersion
      ),
    });
    new apigwv2.WebSocketStage(this, "WebSocketStage", {
      webSocketApi,
      stageName: this.defaultStageName,
      autoDeploy: true,
      throttle: props.throttle,
    });
    webSocketApi.grantManageConnections(handler);

    new CfnRouteResponse(this, "RouteResponse", {
      apiId: webSocketApi.apiId,
      routeId: route.routeId,
      routeResponseKey: "$default",
    });

    this.webSocketApi = webSocketApi;
    this.handler = handler;
    this.handlerLogGroup = handler.logGroup;

    new CfnOutput(this, "WebSocketEndpoint", {
      value: this.apiEndpoint,
    });
  }

  get apiEndpoint() {
    return `${this.webSocketApi.apiEndpoint}/${this.defaultStageName}`;
  }
}
