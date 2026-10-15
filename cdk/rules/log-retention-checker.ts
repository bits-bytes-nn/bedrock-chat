import { Construct } from "constructs";
import { IAspect, Annotations } from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as logs from "aws-cdk-lib/aws-logs";

export class LogRetentionChecker implements IAspect {
  public visit(node: Construct): void {
    const warningMessage =
      "Log retention period is not set. Logs will be kept indefinitely, leading to increased Cloudwatch Logs costs. Set a retention period to reduce costs.";

    if (node instanceof lambda.Function) {
      // A function writes to its own log group, whose retention the CfnLogGroup
      // check covers, or to the default one, whose retention `logRetention` sets.
      const loggingConfig = (node.node.defaultChild as lambda.CfnFunction)
        .loggingConfig as lambda.CfnFunction.LoggingConfigProperty | undefined;
      if (!loggingConfig?.logGroup && node._logRetention === undefined) {
        Annotations.of(node).addWarning(warningMessage);
      }
    } else if (node instanceof logs.CfnLogGroup) {
      if (node.retentionInDays === undefined) {
        Annotations.of(node).addWarning(warningMessage);
      }
    }
  }
}
