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
  /** The chat stack's alarm topic, notified when answers fail. */
  readonly alarmTopicArn: string;
}

export class ApiPublishmentStack extends Stack {
  public readonly chatQueue: sqs.Queue;
  constructor(scope: Construct, id: string, props: ApiPublishmentStackProps) {
    super(scope, id, props);


    const deploymentStage = props.deploymentStage ?? "dev";

    const chatQueueDLQ = new sqs.Queue(this, "ChatQueueDlq", {
      retentionPeriod: cdk.Duration.days(14),
      enforceSSL: true,
    });
    // One retry; the consumer records a failure for the client on the last receive.
    const maxReceiveCount = 2;
    const chatQueue = new sqs.Queue(this, "ChatQueue", {
      visibilityTimeout: cdk.Duration.minutes(30),
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

    const handlerRole = new iam.Role(this, "HandlerRole", {
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
        resources: [props.tableAccessRoleArn],
      })
    );
    handlerRole.addToPolicy(bedrockChatPolicyStatement());
    handlerRole.addToPolicy(
      // Bots with the internet search tool keep their Firecrawl API key here.
      firecrawlSecretPolicyStatement(this, ["secretsmanager:GetSecretValue"])
    );
    const largeMessageBucket = s3.Bucket.fromBucketName(
      this,
      "LargeMessageBucket",
      props.largeMessageBucketName
    );
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
        PUBLISHED_API_ID: id.replace("ApiPublishmentStack", ""),
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
      role: handlerRole,
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
        timeout: cdk.Duration.minutes(15),
        environment: {
          PUBLISHED_API_ID: id.replace("ApiPublishmentStack", ""),
          QUEUE_URL: chatQueue.queueUrl,
          CONVERSATION_TABLE_NAME: props.conversationTableName,
          BOT_TABLE_NAME: props.botTableName,
          CORS_ALLOW_ORIGINS: (props.corsOptions?.allowOrigins ?? ["*"]).join(
            ","
          ),
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
    new cloudwatch.Alarm(this, "FailedAnswers", {
      metric: new logs.MetricFilter(this, "FailedAnswerCount", {
        logGroup: sqsConsumeHandler.logGroup,
        // Logged by backend/app/sqs_consumer.py.
        filterPattern: logs.FilterPattern.literal('"Failed to answer message"'),
        metricNamespace: props.metricsNamespace,
        metricName: `${id}FailedAnswers`,
        metricValue: "1",
      }).metric({ period: cdk.Duration.minutes(5), statistic: "Sum" }),
      threshold: 1,
      evaluationPeriods: 1,
      comparisonOperator:
        cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      alarmDescription: `Published API ${id} could not answer a message.`,
    }).addAlarmAction(alarmAction);

    sqsConsumeHandler.addEventSource(
      // One message per invocation so that a failure does not re-run, and re-bill,
      // the other messages of the batch.
      new lambdaEventSources.SqsEventSource(chatQueue, { batchSize: 1 })
    );
    chatQueue.grantSendMessages(apiHandler);
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
    association.addDependency(api.node.defaultChild as cdk.CfnResource);

    this.chatQueue = chatQueue;

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
