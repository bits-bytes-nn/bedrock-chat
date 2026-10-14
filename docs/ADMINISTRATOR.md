# Administrative features

## Prerequisites

The admin user must be a member of group called `Admin`, which can be set up via the management console > Amazon Cognito User pools or aws cli. Note that the user pool id can be referred by accessing CloudFormation > BedrockChatStack > Outputs > `AuthUserPoolIdxxxx`.

![](./imgs/group_membership_admin.png)

## Mark public bots as Essential

Public bots can be marked as "Essential" by administrators. Bots marked as Essential will be featured in the "Essential" section of the bot store, making them easily accessible to users. This allows administrators to pin important bots that they want all users to use.

### Examples

- HR Assistant Bot: Helps employees with HR-related questions and tasks.
- IT Support Bot: Provides assistance for internal technical issues and account management.
- Internal Policy Guide Bot: Answers frequently asked questions about attendance rules, security policies, and other internal regulations.
- New Employee Onboarding Bot: Guides new hires through procedures and system usage on their first day.
- Benefits Information Bot: Explains company benefit programs and welfare services.

![](./imgs/admin_bot_menue.png)
![](./imgs/bot_store.png)

## Feedback loop

The output from LLM may not always meet the user's expectations. Sometimes it fails to satisfy the user's needs. To effectively "integrate" LLMs into business operations and daily life, implementing a feedback loop is essential. Bedrock Chat is equipped with a feedback feature designed to enable users to analyze why dissatisfaction arose. Based on the analysis results, users can adjust the prompts, RAG data sources, and parameters accordingly.

![](./imgs/feedback_loop.png)

![](./imgs/feedback-using-claude-chat.png)

Data analysts can access to conversation logs using [Amazon Athena](https://aws.amazon.com/jp/athena/). If they want to analyze the data by [Jupyter Notebook](https://jupyter.org/), [this notebook example](../examples/notebooks/feedback_analysis_example.ipynb) can be a reference.

## Dashboard

Currently provides a basic overview of public bot usage, aggregating data for each bot over specified time periods and sorting the results by usage fees.

![](./imgs/admin_bot_analytics.png)

## Notes

- As stated in the [architecture](../README.md#architecture), the admin features will refer to the S3 bucket exported from DynamoDB. Please note that since the export is performed once every hour, the latest conversations may not be reflected immediately.

- The exports contain the full text of conversations, including conversations that users deleted. They expire after `usageAnalysisRetentionDays` (default 90), so usage analysis covers that period. Restrict access to the bucket and Athena accordingly.

- The `TableAccessRole` of `BedrockChatStack` reads and writes the conversation and bot tables. It trusts only roles under the IAM path `/bedrock-chat/<env>/` (`default` for the default environment) and roles named after this stack or `ApiPublishmentStack*`. Creating roles is therefore as sensitive as access to the tables.

- In public bot usages, bots that have not been used at all during the specified period will not be listed.

> [!Important]
> If you're using multiple environments (dev, prod, etc.), the Athena database name will include the environment prefix. Instead of `bedrockchatstack_usage_analysis`, the database name will be:
>
> - For default environment: `bedrockchatstack_usage_analysis`
> - For named environments: `<env-prefix>_bedrockchatstack_usage_analysis` (e.g., `dev_bedrockchatstack_usage_analysis`)
>
> Additionally, the table name will include the environment prefix:
>
> - For default environment: `ddb_export`
> - For named environments: `<env-prefix>_ddb_export` (e.g., `dev_ddb_export`)
>
> Make sure to adjust your queries accordingly when working with multiple environments.

## Download conversation data

You can query the conversation logs by Athena, using SQL. To download logs, open Athena Query Editor from management console and run SQL. Followings are some example queries which are useful to analyze use-cases. Feedback can be referred in `MessageMap` attribute.

### Query per Bot ID

Edit `bot-id` and `datehour`. `bot-id` can be referred on Bot Management screen, where can be accessed from Bot Publish APIs, showing on the left sidebar. Note the end part of the URL like `https://xxxx.cloudfront.net/admin/bot/<bot-id>`.

```sql
SELECT
    d.newimage.PK.S AS UserId,
    d.newimage.SK.S AS ConversationId,
    d.newimage.MessageMap.S AS MessageMap,
    d.newimage.TotalPrice.N AS TotalPrice,
    d.newimage.CreateTime.N AS CreateTime,
    d.newimage.LastMessageId.S AS LastMessageId,
    d.newimage.BotId.S AS BotId,
    d.datehour AS DateHour
FROM
    bedrockchatstack_usage_analysis.ddb_export d
WHERE
    d.newimage.BotId.S = '<bot-id>'
    AND d.datehour BETWEEN '<yyyy/mm/dd/hh>' AND '<yyyy/mm/dd/hh>'
    AND d.Keys.SK.S LIKE CONCAT(d.Keys.PK.S, '#CONV#%')
ORDER BY
    d.datehour DESC;
```

> [!Note]
> If using a named environment (e.g., "dev"), replace `bedrockchatstack_usage_analysis.ddb_export` with `dev_bedrockchatstack_usage_analysis.dev_ddb_export` in the query above.

### Query per User ID

Edit `user-id` and `datehour`. `user-id` can be referred on Bot Management screen.

```sql
SELECT
    d.newimage.PK.S AS UserId,
    d.newimage.SK.S AS ConversationId,
    d.newimage.MessageMap.S AS MessageMap,
    d.newimage.TotalPrice.N AS TotalPrice,
    d.newimage.CreateTime.N AS CreateTime,
    d.newimage.LastMessageId.S AS LastMessageId,
    d.newimage.BotId.S AS BotId,
    d.datehour AS DateHour
FROM
    bedrockchatstack_usage_analysis.ddb_export d
WHERE
    d.newimage.PK.S = '<user-id>'
    AND d.datehour BETWEEN '<yyyy/mm/dd/hh>' AND '<yyyy/mm/dd/hh>'
    AND d.Keys.SK.S LIKE CONCAT(d.Keys.PK.S, '#CONV#%')
ORDER BY
    d.datehour DESC;
```

> [!Note]
> If using a named environment (e.g., "dev"), replace `bedrockchatstack_usage_analysis.ddb_export` with `dev_bedrockchatstack_usage_analysis.dev_ddb_export` in the query above.

## Upgrading

See also [Upgrading an Existing Deployment](../README.md#upgrading-an-existing-deployment) in the README.

`npx cdk deploy --all` updates a deployment in place. DynamoDB adds only one secondary index per table update. If the conversation table has no global secondary index (DynamoDB console > Indexes), deploy commit `d095ec1` first, then v3. Deployments of upstream v3 have `SKIndex` and upgrade in one step.

When you upgrade from upstream:

- The usage analysis export and Athena query result buckets get an expiration of `usageAnalysisRetentionDays` (default 90), so older exports are deleted. Copy them first or raise the value.
- `CreatingBotAllowed` keeps its members, who all joined automatically before (`autoJoinUserGroups` now defaults to `[]`). Review the group in Cognito.

Published APIs keep the code and stack settings they were published with, including the default throttle, alarms, cost metric and metric namespace. Publish them again after upgrading.

## Knowledge sync recovery

While a bot's knowledge sync is queued or running, its owner cannot save the bot (409 with the error code `knowledge_base_syncing`). If the sync timed out or was aborted, the bot stays `RUNNING`: an administrator can save the bot, which queues a new sync, and the owner can delete it. Before saving, check that the earlier ingestion job and knowledge base stack build have ended (Bedrock console and CloudFormation); a new sync that overlaps them can fail again. Saving a bot whose sync failed retries the sync, even if nothing changed. For a dedicated knowledge base the retry synchronizes the whole data source, which also removes files deleted before the failure; for a shared knowledge base it ingests the bot's files again.

A bot can be deleted during a sync. When the sync ends, it deletes the knowledge base stack it built for the deleted bot. If the delete request fails, the alarm for failed sync status updates goes off; a stack whose deletion fails later (`DELETE_FAILED`) raises no alarm ([Alarms and API Throttling](../README.md#alarms-and-api-throttling)); look for `BrChatKbStack*` stacks in the Bedrock region whose bot no longer exists and delete them.

## Deleting a user's data

Deleting a user in Cognito does not delete their conversations or bots. To delete them, run [delete_user_data.py](../backend/scripts/delete_user_data.py) from `backend` with the table names and the large message bucket from the `BedrockChatStack` outputs:

```sh
PYTHONPATH=. CONVERSATION_TABLE_NAME=... BOT_TABLE_NAME=... LARGE_MESSAGE_BUCKET=... REGION=... \
  poetry run python scripts/delete_user_data.py <user-id> [--yes]
```

The user id is the user's `sub` attribute in Cognito, which differs from the Username for users who sign in with an external identity provider. The script lists what it would delete unless you pass `--yes`. Deleting the bots also removes their knowledge base stacks, documents, published APIs and the conversations of those APIs' clients, and other users lose access to the bots this user shared.

The script deletes the bot items directly, without the API's check for publications in progress. Run it when none of the user's bots is being published, and afterwards check that no `ApiPublishmentStack*` stack of the user's bots is left in CloudFormation.

Deleted items stay in the tables' point-in-time recovery backups for up to 35 days, and the usage analysis exports expire after `usageAnalysisRetentionDays`. Unpublishing an API keeps its clients' conversations; they are deleted when the bot is deleted.
