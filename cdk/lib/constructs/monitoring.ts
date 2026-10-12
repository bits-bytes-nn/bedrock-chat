import { CfnOutput, Duration } from "aws-cdk-lib";
import * as cloudwatch from "aws-cdk-lib/aws-cloudwatch";
import { SnsAction } from "aws-cdk-lib/aws-cloudwatch-actions";
import { IFunction } from "aws-cdk-lib/aws-lambda";
import * as sns from "aws-cdk-lib/aws-sns";
import { EmailSubscription } from "aws-cdk-lib/aws-sns-subscriptions";
import * as sfn from "aws-cdk-lib/aws-stepfunctions";
import * as sqs from "aws-cdk-lib/aws-sqs";
import { Construct } from "constructs";

export interface MonitoringProps {
  /** Email address subscribed to the alarm topic. Empty to skip the subscription. */
  readonly alarmEmail: string;
  readonly apiHandler: IFunction;
  readonly webSocketHandler: IFunction;
  readonly embeddingStateMachine: sfn.IStateMachine;
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

    const alarms: [string, cloudwatch.IMetric, number, string][] = [
      [
        "ApiHandlerErrors",
        props.apiHandler.metricErrors({ period: Duration.minutes(5) }),
        5,
        "The REST API handler failed at least 5 times in 5 minutes.",
      ],
      [
        "WebSocketHandlerErrors",
        props.webSocketHandler.metricErrors({ period: Duration.minutes(5) }),
        5,
        "The chat streaming handler failed at least 5 times in 5 minutes.",
      ],
      [
        "WebSocketHandlerThrottles",
        props.webSocketHandler.metricThrottles({ period: Duration.minutes(5) }),
        1,
        "Chat requests were throttled by Lambda concurrency limits.",
      ],
      [
        "KnowledgeSyncFailures",
        props.embeddingStateMachine.metricFailed({ period: Duration.minutes(5) }),
        1,
        "A bot knowledge sync (embedding state machine) failed.",
      ],
      [
        "BotRemovalFailures",
        props.botRemovalDeadLetterQueue.metricApproximateNumberOfMessagesVisible({
          period: Duration.minutes(5),
        }),
        1,
        "Removing a deleted bot's resources failed. Its knowledge base or API stack may still be running and billing.",
      ],
    ];
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
