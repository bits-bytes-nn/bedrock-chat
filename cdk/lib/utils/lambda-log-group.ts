import { Construct } from "constructs";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";

/**
 * The log group of a Lambda function, which keeps its logs for three months.
 * Pass `writer` for a function role without the AWSLambdaBasicExecutionRole policy.
 */
export const lambdaLogGroup = (
  scope: Construct,
  id: string,
  writer?: iam.IGrantable
): logs.LogGroup => {
  const logGroup = new logs.LogGroup(scope, id, {
    retention: logs.RetentionDays.THREE_MONTHS,
  });
  if (writer) {
    logGroup.grantWrite(writer);
  }
  return logGroup;
};
