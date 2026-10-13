import { CfnOutput, RemovalPolicy, Stack } from "aws-cdk-lib";
import {
  AttributeType,
  BillingMode,
  Table,
  TableEncryption,
  StreamViewType,
} from "aws-cdk-lib/aws-dynamodb";
import { AccountPrincipal, Role } from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";

export class Database extends Construct {
  readonly conversationTable: Table;
  readonly botTable: Table;
  readonly tableAccessRole: Role;
  readonly websocketSessionTable: Table;

  constructor(scope: Construct, id: string) {
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

    const tableAccessRole = new Role(this, "TableAccessRole", {
      assumedBy: new AccountPrincipal(Stack.of(this).account),
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
