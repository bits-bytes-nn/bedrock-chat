import { CfnOutput, Duration } from "aws-cdk-lib";
import { IHttpApi } from "aws-cdk-lib/aws-apigatewayv2";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import { SnsAction } from "aws-cdk-lib/aws-cloudwatch-actions";
import { IFunction } from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";
import * as sns from "aws-cdk-lib/aws-sns";
import { EmailSubscription } from "aws-cdk-lib/aws-sns-subscriptions";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import * as sqs from "aws-cdk-lib/aws-sqs";
import { Construct } from "constructs";

export interface MonitoringProps {
  /** Email address subscribed to the alarm topic. Empty to skip the subscription. */
  readonly alarmEmail: string;
  /** Alarm when a day of chat answers costs more than this, in USD. 0 turns it off. */
  readonly dailyChatCostAlarmUsd: number;
  /** Namespace of the metrics that the handlers publish and that log filters count. */
  readonly metricsNamespace: string;
  readonly api: IHttpApi;
  readonly webSocketHandler: IFunction;
  readonly webSocketLogGroup: logs.ILogGroup;
  readonly embeddingStateMachine: sfn.IStateMachine;
  /** Log group of the function that records sync results. */
  readonly syncStatusLogGroup: logs.ILogGroup;
  readonly botRemovalDeadLetterQueue: sqs.IQueue;
}

/** Alarms for failures that users notice: API errors, chat errors and failed knowledge syncs. */
export class Monitoring extends Construct {
  readonly alarmTopic: sns.Topic;

  constructor(scope: Construct, id: string, props: MonitoringProps) {
    super(scope, id);

    this.alarmTopic = new sns.Topic(this, "AlarmTopic", { enforceSSL: true });
    if (props.alarmEmail) {
      this.alarmTopic.addSubscription(new EmailSubscription(props.alarmEmail));
    }
    const action = new SnsAction(this.alarmTopic);

    const period = Duration.minutes(5);
    const minutes = period.toMinutes();
    const errorThreshold = 5;
    // The handlers catch errors and answer with an error, so the Lambda error metric
    // misses them. Count the errors they log instead.
    const loggedErrors = (
      id: string,
      logGroup: logs.ILogGroup,
      terms: string[]
    ): cloudwatch.IMetric =>
      new logs.MetricFilter(this, id, {
        logGroup,
        filterPattern: logs.FilterPattern.anyTerm(...terms),
        metricNamespace: props.metricsNamespace,
        metricName: id,
        metricValue: "1",
      }).metric({ period, statistic: "Sum" });
    const alarms: [string, cloudwatch.IMetric, number, string][] = [
      [
        "ApiServerErrors",
        props.api.metricServerError({ period, statistic: "Sum" }),
        errorThreshold,
        `The REST API answered with a server error at least ${errorThreshold} times in ${minutes} minutes.`,
      ],
      [
        "ChatErrors",
        loggedErrors("ChatErrorCount", props.webSocketLogGroup, [
          // Logged by backend/app/websocket.py.
          "Failed to run stream handler",
          "Bedrock request failed",
          "Bedrock throttled the request",
        ]),
        errorThreshold,
        `Generating chat answers failed at least ${errorThreshold} times in ${minutes} minutes.`,
      ],
      [
        "WebSocketHandlerErrors",
        // Timeouts, out-of-memory and init failures end the invocation before the
        // handler can log, so the log-based count above misses them.
        props.webSocketHandler.metricErrors({ period, statistic: "Sum" }),
        1,
        "The chat handler Lambda failed (for example a timeout, out of memory or an init error).",
      ],
      [
        "WebSocketHandlerThrottles",
        props.webSocketHandler.metricThrottles({ period }),
        1,
        "Chat requests were throttled by Lambda concurrency limits.",
      ],
      [
        "KnowledgeSyncFailures",
        props.embeddingStateMachine.metricFailed({ period }),
        1,
        "The shared knowledge base sync (embedding state machine) failed.",
      ],
      [
        "BotKnowledgeSyncFailures",
        // A failed bot sync ends the execution successfully, so that the other
        // queued bots are still processed.
        loggedErrors("BotKnowledgeSyncFailureCount", props.syncStatusLogGroup, [
          "Knowledge sync failed",
        ]),
        1,
        "A bot knowledge sync failed. The bot shows the reason on its edit page.",
      ],
      [
        "BotRemovalFailures",
        props.botRemovalDeadLetterQueue.metricApproximateNumberOfMessagesVisible({
          period,
        }),
        1,
        "Removing a deleted bot's resources failed. Its knowledge base or API stack may still be running and billing.",
      ],
    ];
    if (props.dailyChatCostAlarmUsd > 0) {
      alarms.push([
        "DailyChatCost",
        new cloudwatch.Metric({
          // Published by backend/app/websocket.py (emit_chat_cost).
          namespace: props.metricsNamespace,
          metricName: "ChatCost",
          statistic: "Sum",
          period: Duration.days(1),
        }),
        props.dailyChatCostAlarmUsd,
        `Chat answers cost at least ${props.dailyChatCostAlarmUsd} USD in a day, by the model prices in the backend.`,
      ]);
    }
    for (const [alarmId, metric, threshold, description] of alarms) {
      new cloudwatch.Alarm(this, alarmId, {
        metric,
        threshold,
        evaluationPeriods: 1,
        comparisonOperator:
          cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
        alarmDescription: description,
      }).addAlarmAction(action);
    }

    new CfnOutput(this, "AlarmTopicArn", { value: this.alarmTopic.topicArn });
  }
}
