import { CfnOutput, RemovalPolicy, Stack } from "aws-cdk-lib";
import {
  AttributeType,
  BillingMode,
  ProjectionType,
  Table,
  TableEncryption,
  StreamViewType,
} from "aws-cdk-lib/aws-dynamodb";
import { AccountPrincipal, Role } from "aws-cdk-lib/aws-iam";
import { tableAccessRolePath } from "../utils/table-access";
import { apiPublishmentStackPrefix } from "../utils/stack-names";
import { Construct } from "constructs";

export interface DatabaseProps {
  /** Environment prefix, part of the path of the roles that may access the tables. */
  readonly envPrefix: string;
}

export class Database extends Construct {
  readonly conversationTable: Table;
  readonly botTable: Table;
  readonly tableAccessRole: Role;
  /** Path for the roles that assume the table access role. */
  readonly tableAccessRolePath: string;
  readonly websocketSessionTable: Table;

  constructor(scope: Construct, id: string, props: DatabaseProps) {
    super(scope, id);

    // Conversation Table
    const conversationTable = new Table(this, "ConversationTableV3", {
      // PK: UserId
      partitionKey: { name: "PK", type: AttributeType.STRING },
      // SK: ConversationId
      sortKey: { name: "SK", type: AttributeType.STRING },
      billingMode: BillingMode.PAY_PER_REQUEST,
      // Keep user data when the stack is deleted or a deployment replaces the table.
      removalPolicy: RemovalPolicy.RETAIN,
      deletionProtection: true,
      stream: StreamViewType.NEW_IMAGE,
      // Needed to export the data to S3 for usage analysis.
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      encryption: TableEncryption.AWS_MANAGED,
    });
    // No longer used by this backend, but published API stacks built from older
    // versions query it, and DynamoDB changes only one index per update: removing it
    // while adding the index below would fail upgrades. Remove it in a later
    // release, after republishing the APIs.
    conversationTable.addGlobalSecondaryIndex({
      indexName: "SKIndex",
      partitionKey: { name: "SK", type: AttributeType.STRING },
    });

    // Lists conversations without reading their messages. Only conversation items
    // have CreateTime, so related documents stay out of the index.
    conversationTable.addGlobalSecondaryIndex({
      indexName: "ConversationListIndex",
      partitionKey: { name: "PK", type: AttributeType.STRING },
      sortKey: { name: "CreateTime", type: AttributeType.NUMBER },
      projectionType: ProjectionType.INCLUDE,
      nonKeyAttributes: ["Title", "BotId"],
    });

    // Bot Table
    const botTable = new Table(this, "BotTableV3", {
      // PK: UserId
      partitionKey: { name: "PK", type: AttributeType.STRING },
      // SK: ItemType
      sortKey: { name: "SK", type: AttributeType.STRING },
      billingMode: BillingMode.PAY_PER_REQUEST,
      // Keep user data when the stack is deleted or a deployment replaces the table.
      removalPolicy: RemovalPolicy.RETAIN,
      deletionProtection: true,
      stream: StreamViewType.NEW_IMAGE,
      // Need to enable PITR for bot table for Zero-ETL pipeline
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      encryption: TableEncryption.AWS_MANAGED,
    });
    // LSI-1
    botTable.addLocalSecondaryIndex({
      indexName: "StarredIndex",
      sortKey: { name: "IsStarred", type: AttributeType.STRING },
    });
    // LSI-2
    botTable.addLocalSecondaryIndex({
      indexName: "LastUsedTimeIndex",
      sortKey: { name: "LastUsedTime", type: AttributeType.NUMBER },
    });
    // GSI-1
    botTable.addGlobalSecondaryIndex({
      indexName: "BotIdIndex",
      partitionKey: { name: "BotId", type: AttributeType.STRING },
    });
    // GSI-2
    botTable.addGlobalSecondaryIndex({
      indexName: "SharedScopeIndex",
      partitionKey: { name: "SharedScope", type: AttributeType.STRING },
      sortKey: { name: "SharedStatus", type: AttributeType.STRING },
    });
    // GSI-3
    botTable.addGlobalSecondaryIndex({
      indexName: "ItemTypeIndex",
      partitionKey: { name: "ItemType", type: AttributeType.STRING },
    });
    // GSI-4
    botTable.addGlobalSecondaryIndex({
      indexName: "SyncStatusIndex",
      partitionKey: {
        name: "SyncStatus",
        type: AttributeType.STRING,
      },
    });

    // Assumed by the Lambda roles of this stack and of the published API stacks
    // (cdk/bin/api-publish.ts), which are created under this path. The name patterns
    // keep roles created before the path was introduced working, such as those of
    // APIs published earlier.
    const { partition, account, stackName } = Stack.of(this);
    this.tableAccessRolePath = tableAccessRolePath(props.envPrefix);
    const tableAccessRole = new Role(this, "TableAccessRole", {
      assumedBy: new AccountPrincipal(account).withConditions({
        ArnLike: {
          "aws:PrincipalArn": [
            `arn:${partition}:iam::${account}:role/${stackName}-*`,
            `arn:${partition}:iam::${account}:role/${apiPublishmentStackPrefix}*`,
            `arn:${partition}:iam::${account}:role${this.tableAccessRolePath}*`,
          ],
        },
      }),
    });
    conversationTable.grantReadWriteData(tableAccessRole);
    botTable.grantReadWriteData(tableAccessRole);

    // Websocket session table.
    // This table is used to concatenate user input exceeding 32KB which is the limit of API Gateway.
    const websocketSessionTable = new Table(this, "WebsocketSessionTable", {
      partitionKey: { name: "ConnectionId", type: AttributeType.STRING },
      sortKey: { name: "MessagePartId", type: AttributeType.NUMBER },
      billingMode: BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
      timeToLiveAttribute: "expire",
    });

    this.conversationTable = conversationTable;
    this.botTable = botTable;
    this.tableAccessRole = tableAccessRole;
    this.websocketSessionTable = websocketSessionTable;

    new CfnOutput(this, "ConversationTableName", {
      value: conversationTable.tableName,
    });
    new CfnOutput(this, "BotTableName", {
      value: botTable.tableName,
    });
  }
}
