# API Publication

## Overview

This sample includes a feature for publishing APIs. While a chat interface can be convenient for preliminary validation, the actual implementation depends on the specific use case and user experience (UX) desired for the end-user. In some scenarios, a chat UI may be the preferred choice, while in others, stand-alone API might be more suitable. After initial validation, this sample provides the capability to publish customized bots according to the project's needs. By entering settings for quotas, throttling, origins, etc., an endpoint can be published along with an API key, offering flexibility for diverse integration options.

## Security

Using only an API key is not recommended as described in: [AWS API Gateway Developer Guide](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-api-usage-plans.html). Consequently, this sample implements a simple IP address restriction via AWS WAF. The WAF rule is applied commonly across the application due to cost considerations, under the assumption that the sources one would want to restrict are likely the same across all issued APIs. **Please adhere to your organization's security policy for actual implementation.** Also see [Architecture](#architecture) section.

## How to publish customized bot API

### Prerequisites

For governance reasons, only limited users are able to publish bots. Before publishing, the user must be a member of group called `PublishAllowed`, which can be set up via the management console > Amazon Cognito User pools or aws cli. Note that the user pool id can be referred by accessing CloudFormation > BedrockChatStack > Outputs > `AuthUserPoolIdxxxx`.

![](./imgs/group_membership_publish_allowed.png)

### API Publish Settings

After logging in as a `PublishAllowed` user and create a bot, choose `API PublishSettings`. Note that only a shared bot can be published.
![](./imgs/bot_api_publish_screenshot.png)

On the following screen, we can configure several parameters regarding throttling. For the detail, please also see: [Throttle API requests for better throughput](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-request-throttling.html).
![](./imgs/bot_api_publish_screenshot2.png)

After deployment, following screen will appear where you can get the endpoint url and a api key. We can also add and delete api keys.

![](./imgs/bot_api_publish_screenshot3.png)

## Architecture

The API is published as following diagram:

![](./imgs/published_arch.png)

The WAF is used for ip address restriction. The address can be configured by setting parameters `publishedApiAllowedIpV4AddressRanges` and `publishedApiAllowedIpV6AddressRanges` in `cdk.json`.

Once a user click publish the bot, [AWS CodeBuild](https://aws.amazon.com/codebuild/) launch CDK deployment task to provision the API stack (Also see: [CDK definition](../cdk/lib/api-publishment-stack.ts)) which contains API Gateway, Lambda and SQS. SQS is used to decouple user request and LLM operation because generating output may exceed 30sec, which is the limit of API Gateway quota. To fetch the output, need to access the API asynchronously. For more the detail, see [API Specification](#api-specification).

Client needs to set `x-api-key` on the request header.

Published APIs keep the backend version and stack settings they were published with. After upgrading Bedrock Chat, publish each API again to update it. For example, an API published before Tavily and Brave Search were added fails to load a bot that uses them, and searches with DuckDuckGo once the bot's Firecrawl settings are saved again.

`GET /conversation/{conversationId}/{messageId}` returns 404 while the answer is not ready, and 500 with the reason when it could not be generated. The API stack has `FailedAnswers` and `ChatQueueDlqMessages` alarms for such failures and alarms for errors of its Lambda functions; they notify the chat stack's `AlarmTopicArn` topic. Requests with `continueGenerate` are rejected with 400, and a message larger than the queue limit of 1 MiB with 413. Answers are generated with limited concurrency, so a burst of requests waits in the queue. A failed answer is retried once, about 30 seconds later; invalid requests, missing bots, messages or conversations that are too large and conversations too long for the model fail at once.

Without throttling settings, a published API allows 10 requests per second with a burst of 20, so that a leaked key cannot run up model costs unchecked. Throttling (rate and burst) and quota (limit and period) must each be set completely or not at all; otherwise the publish request is rejected (422).

While a publication build runs, publishing, unpublishing and deleting the bot return 409 with the error code `api_publishing`; try again after the build finishes. Publishing again while the previous API stack is still being deleted returns 409 with the error code `api_unpublishing`; publish again after the deletion finishes.

While a bot is not published, its API settings (`GET /bot/{bot_id}/publication`) return the error code `bot_not_published`. Unpublishing an API keeps its clients' conversations; they are deleted when the bot is deleted.

## API specification

The [published specification](https://aws-samples.github.io/bedrock-chat) is the upstream project's. For this fork, run the backend locally (see [backend/README.md](../backend/README.md)) and open `/docs` or `/openapi.json`.
