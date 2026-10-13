import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import { SnsAction } from "aws-cdk-lib/aws-cloudwatch-actions";
import * as sns from "aws-cdk-lib/aws-sns";
import * as cdk from "aws-cdk-lib";
import { CfnOutput, Stack, StackProps } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import { DockerImageCode, DockerImageFunction } from "aws-cdk-lib/aws-lambda";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambdaEventSources from "aws-cdk-lib/aws-lambda-event-sources";
import * as path from "path";
import { Platform } from "aws-cdk-lib/aws-ecr-assets";
import * as wafv2 from "aws-cdk-lib/aws-wafv2";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as logs from "aws-cdk-lib/aws-logs";
import { excludeDockerImage } from "./constants/docker";
import { apiPublishmentStackPrefix } from "./utils/stack-names";
import {
  bedrockChatPolicyStatement,
  firecrawlSecretPolicyStatement,
} from "./utils/bedrock-policies";

interface ApiPublishmentStackProps extends StackProps {
  readonly bedrockRegion: string;
  readonly enableBedrockGlobalInference: boolean;
  readonly enableBedrockCrossRegionInference: boolean;
  readonly conversationTableName: string;
  readonly botTableName: string;
  readonly tableAccessRoleArn: string;
  readonly webAclArn: string;
  readonly usagePlan: apigateway.UsagePlanProps;
  readonly deploymentStage?: string;
  readonly largeMessageBucketName: string;
  /** Model allowlist and defaults of the main API. */
  readonly modelEnvironment: Record<string, string>;
  readonly corsOptions?: apigateway.CorsOptions;
  /** Namespace of the ChatCost metric, shared with the chat stack's alarm. */
  readonly metricsNamespace: string;
  /** Path that the chat stack's table access role trusts. */
  readonly tableAccessRolePath: string;
  /** The chat stack's alarm topic, notified when answers fail. */
  readonly alarmTopicArn: string;
}

// The consumer runs for up to 15 minutes per message. SQS needs a visibility timeout of
// at least six times the function timeout, so that a message is not received again
// while the event source mapping still retries a throttled invocation.
const CONSUMER_TIMEOUT = cdk.Duration.minutes(15);
// Concurrent answers per published API. Each answer calls the model, so this bounds
// the model cost and quota that one API key can use at a time, and keeps one API from
// taking the account's Lambda concurrency.
const CONSUMER_MAX_CONCURRENCY = 10;

export class ApiPublishmentStack extends Stack {
  constructor(scope: Construct, id: string, props: ApiPublishmentStackProps) {
    super(scope, id, props);

    const deploymentStage = props.deploymentStage ?? "dev";
    // Read by the backend as PUBLISHED_API_ID.
    const publishedApiId = id.replace(apiPublishmentStackPrefix, "");

    const chatQueueDLQ = new sqs.Queue(this, "ChatQueueDlq", {
      retentionPeriod: cdk.Duration.days(14),
      enforceSSL: true,
    });
    // One retry; the consumer records a failure for the client on the last receive.
    const maxReceiveCount = 2;
    const chatQueue = new sqs.Queue(this, "ChatQueue", {
      visibilityTimeout: cdk.Duration.seconds(CONSUMER_TIMEOUT.toSeconds() * 6),
      enforceSSL: true,
      deadLetterQueue: {
        maxReceiveCount,
        queue: chatQueueDLQ,
      },
    });
    const alarmAction = new SnsAction(
      sns.Topic.fromTopicArn(this, "AlarmTopic", props.alarmTopicArn)
    );
    new cloudwatch.Alarm(this, "ChatQueueDlqMessages", {
      metric: chatQueueDLQ.metricApproximateNumberOfMessagesVisible({
        period: cdk.Duration.minutes(5),
      }),
      threshold: 1,
      evaluationPeriods: 1,
      comparisonOperator:
        cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      alarmDescription: `Published API ${id} could not answer messages.`,
    }).addAlarmAction(alarmAction);

    // Both handlers read bots and conversations through the table access role. Loading
    // a bot with the internet search tool reads its Firecrawl API key.
    const newHandlerRole = (roleId: string): iam.Role => {
      const role = new iam.Role(this, roleId, {
        path: props.tableAccessRolePath,
        assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      });
      role.addManagedPolicy(
        iam.ManagedPolicy.fromAwsManagedPolicyName(
          "service-role/AWSLambdaBasicExecutionRole"
        )
      );
      role.addToPolicy(
        // Assume the table access role for row-level access control.
        new iam.PolicyStatement({
          actions: ["sts:AssumeRole"],
          resources: [props.tableAccessRoleArn],
        })
      );
      role.addToPolicy(
        firecrawlSecretPolicyStatement(this, ["secretsmanager:GetSecretValue"])
      );
      return role;
    };
    const largeMessageBucket = s3.Bucket.fromBucketName(
      this,
      "LargeMessageBucket",
      props.largeMessageBucketName
    );
    // The API handler queues messages and reads conversations. It does not call models.
    const apiHandlerRole = newHandlerRole("ApiHandlerRole");
    largeMessageBucket.grantRead(apiHandlerRole);
    // The consumer generates the answers.
    const handlerRole = newHandlerRole("HandlerRole");
    handlerRole.addToPolicy(bedrockChatPolicyStatement());
    largeMessageBucket.grantReadWrite(handlerRole);

    // Handler for FastAPI
    const apiHandler = new DockerImageFunction(this, "ApiHandler", {
      code: DockerImageCode.fromImageAsset(
        path.join(__dirname, "../../backend"),
        {
          platform: Platform.LINUX_AMD64,
          file: "Dockerfile",
          exclude: [...excludeDockerImage],
        }
      ),
      memorySize: 1024,
      // API Gateway ends the request after 29 seconds, so a longer run is wasted.
      timeout: cdk.Duration.seconds(30),
      environment: {
        PUBLISHED_API_ID: publishedApiId,
        QUEUE_URL: chatQueue.queueUrl,
        CONVERSATION_TABLE_NAME: props.conversationTableName,
        BOT_TABLE_NAME: props.botTableName,
        CORS_ALLOW_ORIGINS: (props.corsOptions?.allowOrigins ?? ["*"]).join(
          ","
        ),
        ACCOUNT: Stack.of(this).account,
        REGION: Stack.of(this).region,
        BEDROCK_REGION: props.bedrockRegion,
        LARGE_MESSAGE_BUCKET: props.largeMessageBucketName,
        ...props.modelEnvironment,
        TABLE_ACCESS_ROLE_ARN: props.tableAccessRoleArn,
      },
      role: apiHandlerRole,
      logRetention: logs.RetentionDays.THREE_MONTHS,
    });

    // Handler for SQS consumer
    const sqsConsumeHandler = new DockerImageFunction(
      this,
      "SqsConsumeHandler",
      {
        code: DockerImageCode.fromImageAsset(
          path.join(__dirname, "../../backend"),
          {
            platform: Platform.LINUX_AMD64,
            file: "lambda.Dockerfile",
            cmd: ["app.sqs_consumer.handler"],
            exclude: [...excludeDockerImage],
          }
        ),
        memorySize: 1024,
        timeout: CONSUMER_TIMEOUT,
        environment: {
          // Dimension of the FailedAnswers metric.
          PUBLISHED_API_ID: publishedApiId,
          // The consumer shortens the visibility timeout of a message to retry.
          QUEUE_URL: chatQueue.queueUrl,
          CONVERSATION_TABLE_NAME: props.conversationTableName,
          BOT_TABLE_NAME: props.botTableName,
          ACCOUNT: Stack.of(this).account,
          REGION: Stack.of(this).region,
          ENABLE_BEDROCK_GLOBAL_INFERENCE:
            props.enableBedrockGlobalInference.toString(),
          ENABLE_BEDROCK_CROSS_REGION_INFERENCE:
            props.enableBedrockCrossRegionInference.toString(),
          BEDROCK_REGION: props.bedrockRegion,
          // Conversations over the DynamoDB item limit are stored in this bucket.
          LARGE_MESSAGE_BUCKET: props.largeMessageBucketName,
          TABLE_ACCESS_ROLE_ARN: props.tableAccessRoleArn,
          METRICS_NAMESPACE: props.metricsNamespace,
          MAX_RECEIVE_COUNT: maxReceiveCount.toString(),
          ...props.modelEnvironment,
        },
        role: handlerRole,
        logRetention: logs.RetentionDays.THREE_MONTHS,
      }
    );
    // Failures that the consumer records for the client end the message normally,
    // so they never reach the dead-letter queue.
    const period = cdk.Duration.minutes(5);
    const alarms: [string, cloudwatch.IMetric, string][] = [
      [
        "FailedAnswers",
        new cloudwatch.Metric({
          // Published by backend/app/sqs_consumer.py.
          namespace: props.metricsNamespace,
          metricName: "FailedAnswers",
          dimensionsMap: { PublishedApiId: publishedApiId },
          statistic: "Sum",
          period,
        }),
        `Published API ${id} could not answer a message.`,
      ],
      [
        "ApiHandlerErrors",
        apiHandler.metricErrors({ period }),
        `The API handler of published API ${id} failed (for example a timeout or an init error).`,
      ],
      [
        "SqsConsumeHandlerErrors",
        // Messages to retry are reported as batch item failures, not errors. Errors
        // are failures that escape the handler (backend/app/sqs_consumer.py): timeouts,
        // out-of-memory and init failures, unparsable messages, and failures to check
        // or record a failed answer.
        sqsConsumeHandler.metricErrors({ period }),
        `The queue consumer of published API ${id} failed (for example a timeout or an init error).`,
      ],
    ];
    for (const [alarmId, metric, description] of alarms) {
      new cloudwatch.Alarm(this, alarmId, {
        metric,
        threshold: 1,
        evaluationPeriods: 1,
        comparisonOperator:
          cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
        alarmDescription: description,
      }).addAlarmAction(alarmAction);
    }

    sqsConsumeHandler.addEventSource(
      // One message per invocation so that a failure does not re-run, and re-bill,
      // the other messages of the batch.
      new lambdaEventSources.SqsEventSource(chatQueue, {
        batchSize: 1,
        maxConcurrency: CONSUMER_MAX_CONCURRENCY,
        reportBatchItemFailures: true,
      })
    );
    chatQueue.grantSendMessages(apiHandler);
    // Includes sqs:ChangeMessageVisibility on this queue.
    chatQueue.grantConsumeMessages(sqsConsumeHandler);

    const api = new apigateway.LambdaRestApi(this, "Api", {
      restApiName: id,
      handler: apiHandler,
      proxy: true,
      deployOptions: {
        stageName: deploymentStage,
      },
      defaultMethodOptions: { apiKeyRequired: true },
      defaultCorsPreflightOptions: props.corsOptions,
    });

    const apiKey = api.addApiKey("ApiKey", {
      description: "Default api key (Auto generated by CDK)",
    });
    const usagePlan = api.addUsagePlan("UsagePlan", {
      ...props.usagePlan,
    });
    usagePlan.addApiKey(apiKey);
    usagePlan.addApiStage({ stage: api.deploymentStage });

    const association = new wafv2.CfnWebACLAssociation(
      this,
      "WebAclAssociation",
      {
        resourceArn: `arn:${this.partition}:apigateway:${this.region}::/restapis/${api.restApiId}/stages/${api.deploymentStage.stageName}`,
        webAclArn: props.webAclArn,
      }
    );
    // The ARN names the stage without referencing it, so wait for the stage.
    association.node.addDependency(api.deploymentStage);

    new CfnOutput(this, "ApiId", {
      value: api.restApiId,
    });
    new CfnOutput(this, "ApiName", {
      value: api.restApiName,
    });
    new CfnOutput(this, "ApiUsagePlanId", {
      value: usagePlan.usagePlanId,
    });
    new CfnOutput(this, "AllowedOrigins", {
      value: props.corsOptions?.allowOrigins?.join(",") ?? "*",
    });
    new CfnOutput(this, "DeploymentStage", {
      value: deploymentStage,
    });
  }
}
