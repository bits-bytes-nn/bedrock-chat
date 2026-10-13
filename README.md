<h1 align="center">Bedrock Chat (BrChat)</h1>

<p align="center">
  <img src="https://img.shields.io/github/v/release/aws-samples/bedrock-chat?style=flat-square" />
  <img src="https://img.shields.io/github/license/aws-samples/bedrock-chat?style=flat-square" />
  <img src="https://img.shields.io/github/actions/workflow/status/aws-samples/bedrock-chat/cdk.yml?style=flat-square" />
  <a href="https://github.com/aws-samples/bedrock-chat/issues?q=is%3Aissue%20state%3Aopen%20label%3Aroadmap">
    <img src="https://img.shields.io/badge/roadmap-view-blue?style=flat-square" />
  </a>
</p>

[English](./README.md) | [日本語](./docs/README_ja-JP.md) | [한국어](./docs/README_ko-KR.md) | [中文](./docs/README_zh-CN.md) | [Français](./docs/README_fr-FR.md) | [Deutsch](./docs/README_de-DE.md) | [Español](./docs/README_es-ES.md) | [Italian](./docs/README_it-IT.md) | [Norsk](./docs/README_nb-NO.md) | [ไทย](./docs/README_th-TH.md) | [Bahasa Melayu](./docs/README_ms-MY.md) | [Tiếng Việt](./docs/README_vi-VN.md) | [Polski](./docs/README_pl-PL.md) | [Português Brasil](./docs/README_pt-BR.md)

> [!NOTE]
> The translations describe the upstream aws-samples project and are not updated with this fork. The English README is the reference for models, defaults and deployment options.

### Changes from upstream

This fork of [aws-samples/bedrock-chat](https://github.com/aws-samples/bedrock-chat) differs in these ways:

- Current Claude and OpenAI models on Bedrock; retired models stay readable but cannot be selected ([models](#deploy-using-cdk)).
- PowerPoint parsing and audio/video transcription for chat attachments and knowledge files ([presentations and recordings](#presentations-and-recordings)).
- Claude Haiku 4.5 as the knowledge base parsing model ([parsing](#knowledge-base-parsing)).
- Self sign-up off by default, and user data (tables, user pool, buckets) retained when the stack is deleted ([remove resources](#remove-resources)).
- Only administrators can attach existing knowledge bases, S3 sources and Bedrock agents to bots.
- New users join no group (`autoJoinUserGroups` defaults to `[]`) ([groups](#add-new-users-to-groups-automatically)).
- A per-user limit on bots with dedicated knowledge bases, `maxDedicatedKnowledgeBasesPerUser` ([limit](#limit-dedicated-knowledge-bases)).
- CloudWatch alarms, including a daily chat cost alarm, and API throttling ([alarms](#alarms-and-api-throttling)).
- WebSocket connections need a valid ID token at `$connect` ([alarms and throttling](#alarms-and-api-throttling)).
- The REST API allows CORS only from the app origins and `http://localhost:5173` ([local development](./docs/LOCAL_DEVELOPMENT.md#frontend-development)).
- Published APIs default to 10 requests per second with a burst of 20, and alarm on failed answers ([API publication](./docs/PUBLISH_API.md#architecture)).
- Usage analysis exports expire after `usageAnalysisRetentionDays` (default 90) ([retention](#usage-analysis-retention)).
- A script that deletes a user's conversations and bots ([deleting a user's data](./docs/ADMINISTRATOR.md#deleting-a-users-data)).
- Conversation writes that merge concurrent updates instead of overwriting them.

A multilingual generative AI platform powered by [Amazon Bedrock](https://aws.amazon.com/bedrock/).
Supports chat, custom bots with knowledge (RAG), bot sharing via a bot store, and task automation using agents.

![](./docs/imgs/demo.gif)

> [!Warning]
>
> **V3 released. To update, please carefully review the [migration guide](./docs/migration/V2_TO_V3.md).** Without any care, **BOTS FROM V2 WILL BECOME UNUSABLE.**

### Bot Personalization / Bot store

Add your own instruction and knowledge (a.k.a [RAG](https://aws.amazon.com/what-is/retrieval-augmented-generation/). The bot can be shared among application users via bot store market place. The customized bot also can be published as stand-alone API (See the [detail](./docs/PUBLISH_API.md)).

<details>
<summary>Screenshots</summary>

![](./docs/imgs/customized_bot_creation.png)
![](./docs/imgs/fine_grained_permission.png)
![](./docs/imgs/bot_store.png)
![](./docs/imgs/bot_api_publish_screenshot3.png)

Administrators can also import existing [Amazon Bedrock's KnowledgeBase](https://aws.amazon.com/bedrock/knowledge-bases/).

![](./docs/imgs/import_existing_kb.png)

</details>

> [!Important]
> For governance reasons, only allowed users are able to create customized bots. To allow the creation of customized bots, the user must be a member of group called `CreatingBotAllowed`, which can be set up via the management console > Amazon Cognito User pools or aws cli. Note that the user pool id can be referred by accessing CloudFormation > BedrockChatStack > Outputs > `AuthUserPoolIdxxxx`.

### Multi-Tenant Usage of Knowledge Base

In Amazon Bedrock Knowledge Bases, by default, the number of Knowledge Bases that can be created in a single AWS account is limited to 100. To work around this limitation, you can use 'multi-tenant' mode, where a Knowledge Base with common settings is shared among multiple bots, and files uploaded by each bot are filtered by attaching the Bot ID as metadata.

Newly created bots will have multi-tenant mode enabled by default. To migrate existing bots to multi-tenant mode, change the bot's knowledge settings to "Create a tenant in a shared Knowledge Base."

To migrate multiple bots to multi-tenant mode in bulk, execute commands like the following:

```bash
aws dynamodb execute-statement --statement "UPDATE \"$BotTableNameV3\" SET BedrockKnowledgeBase.type='shared' SET SyncStatus='QUEUED' WHERE PK='$UserID' AND SK='BOT#$BotID'"
# Execute for all target bots

aws stepfunctions start-execution --state-machine-arn $EmbeddingStateMachineArn
```

### Administrative features

API Management, Mark bots as essential, Analyze usage for bots. [detail](./docs/ADMINISTRATOR.md)

<details>
<summary>Screenshots</summary>

![](./docs/imgs/admin_bot_menue.png)
![](./docs/imgs/bot_store.png)
![](./docs/imgs/admn_api_management.png)
![](./docs/imgs/admin_bot_analytics.png)

</details>

### Agent

By using the [Agent functionality](./docs/AGENT.md), your chatbot can automatically handle more complex tasks. For example, to answer a user's question, the Agent can retrieve necessary information from external tools or break down the task into multiple steps for processing.

<details>
<summary>Screenshots</summary>

![](./docs/imgs/agent1.png)
![](./docs/imgs/agent2.png)

</details>

### Presentations and recordings

Chat attachments and bot knowledge files can also be PowerPoint presentations (`.pptx`) and recordings (`.mp3`, `.mp4`, `.wav`, `.flac`, `.ogg`, `.amr`, `.webm`, `.m4a`), which Bedrock cannot read directly. They are converted to text after the upload:

- Presentations are parsed for slide text, tables and speaker notes (up to 100 MB).
- Recordings are transcribed with Amazon Transcribe (up to 500 MB). The spoken language is identified among Korean, English, Japanese and Chinese, and speakers are labeled.

A knowledge file is registered as `<filename>.txt`. A chat attachment is sent as text. Transcription runs in the Bedrock Region and is billed per minute of audio; see [Amazon Transcribe pricing](https://aws.amazon.com/transcribe/pricing/).

### Knowledge base parsing

The bot's knowledge settings offer an advanced parsing model that reads figures, charts and tables in PDF files and images. Claude Haiku 4.5 is called through a global cross-Region inference profile, so documents may be processed in other Regions. Claude 3 Haiku is kept as a legacy option and is not available in every Region. Bots saved with Claude 3 or 3.5 Sonnet, which Bedrock no longer offers, use the default parser.

> [!NOTE]
> OpenSearch Serverless returns newly indexed documents about a minute after ingestion, so a sync is marked as succeeded a minute after its ingestion completes.

## 🎓Workshop

A comprehensive workshop is available [here](https://catalog.us-east-1.prod.workshops.aws/workshops/4bf8d30b-f7c9-440a-a853-9394a41909d2/en-US).

<details>
<summary>Screenshot</summary>

![](./docs/imgs/workshop.png)

</details>

## 🚀 Super-easy Deployment

- In the us-east-1 region, open [Bedrock Model access](https://us-east-1.console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess) > `Manage model access` > Check all of models you wish to use and then `Save changes`.

<details>
<summary>Screenshot</summary>

![](./docs/imgs/model_screenshot.png)

</details>

### Supported regions

Please make sure that you deploy Bedrock Chat in a region [where OpenSearch Serverless and Ingestion APIs are available](https://docs.aws.amazon.com/general/latest/gr/opensearch-service.html), if you want to use bots and create knowledge bases (OpenSearch Serverless is the default choice). The following regions are supported: us-east-1, us-east-2, us-west-1, us-west-2, ap-south-1, ap-northeast-1, ap-northeast-2, ap-southeast-1, ap-southeast-2, ca-central-1, eu-central-1, eu-west-1, eu-west-2, eu-south-2, eu-north-1, sa-east-1

For the **bedrock-region** parameter you need to choose a region [where Bedrock is available](https://docs.aws.amazon.com/general/latest/gr/bedrock.html).

- Open [CloudShell](https://console.aws.amazon.com/cloudshell/home) at the region where you want to deploy
- Run deployment via following commands. If you want to specify the version to deploy or need to apply security policies, please specify the appropriate parameters from [Optional Parameters](#optional-parameters).

```sh
git clone https://github.com/aws-samples/bedrock-chat.git
cd bedrock-chat
chmod +x bin.sh
./bin.sh
```

> [!IMPORTANT]
> `bin.sh` runs the deployment from the repository in `--repo-url`, which defaults to upstream aws-samples/bedrock-chat. To deploy this fork, pass its URL, for example `./bin.sh --repo-url https://github.com/bits-bytes-nn/bedrock-chat.git`. When the deployment finishes, `bin.sh` deletes the `CodeBuildForDeploy` stack, whose CodeBuild project has administrator access.

- You will be asked if a new user or using v3. If you are not a continuing user from v0, please enter `y`.

### Optional Parameters

You can specify the following parameters during deployment to enhance security and customization:

- **--enable-self-register**: Allow anyone who can reach the URL to sign up (default: disabled, so users are created in Cognito by an administrator). Combine it with `--allowed-signup-email-domains` and IP restrictions.
- **--enable-lambda-snapstart**: Enable [Lambda SnapStart](https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html) (default: disabled). If this flag is set, improves cold start times for Lambda functions, providing faster response times for better user experience.
- **--ipv4-ranges**: Comma-separated list of allowed IPv4 ranges. (default: allow all ipv4 addresses)
- **--ipv6-ranges**: Comma-separated list of allowed IPv6 ranges. (default: allow all ipv6 addresses)
- **--disable-ipv6**: Disable connections over IPv6. (default: enabled)
- **--allowed-signup-email-domains**: Comma-separated list of allowed email domains for sign-up. (default: no domain restriction)
- **--bedrock-region**: Define the region where bedrock is available. (default: us-east-1)
- **--repo-url**: The custom repo of Bedrock Chat to deploy, if forked or custom source control. (default: https://github.com/aws-samples/bedrock-chat.git)
- **--version**: The version of Bedrock Chat to deploy. (default: latest version in development)
- **--cdk-json-override**: You can override any CDK context values during deployment using the override JSON block. This allows you to modify the configuration without editing the cdk.json file directly.

Example usage:

```bash
./bin.sh --cdk-json-override '{
  "context": {
    "selfSignUpEnabled": false,
    "enableLambdaSnapStart": true,
    "allowedIpV4AddressRanges": ["192.168.1.0/24"],
    "allowedCountries": ["US", "CA"],
    "allowedSignUpEmailDomains": ["example.com"],
    "globalAvailableModels": [
      "claude-v5.5-sonnet",
      "claude-v5.5-haiku",
      "amazon-nova-pro",
      "amazon-nova-lite",
      "llama3-3-70b-instruct"
    ]
  }
}'
```

The override JSON must follow the same structure as cdk.json. You can override any context values including:

- `selfSignUpEnabled`
- `enableLambdaSnapStart`
- `allowedIpV4AddressRanges`
- `allowedIpV6AddressRanges`
- `allowedCountries`
- `allowedSignUpEmailDomains`
- `bedrockRegion`
- `enableRagReplicas`
- `enableBedrockCrossRegionInference`
- `globalAvailableModels`: accepts a list of model IDs to enable. The default value is an empty list, which enables all models.
- `logoPath`: relative path to the logo asset within the frontend `public/` directory that appears at the top of the navigation drawer.
- And other context values defined in cdk.json

> [!Note]
> The override values will be merged with the existing cdk.json configuration during the deployment time in the AWS code build. Values specified in the override will take precedence over the values in cdk.json.

#### Example command with parameters:

```sh
./bin.sh --ipv4-ranges "192.0.2.0/25,192.0.2.128/25" --ipv6-ranges "2001:db8:1:2::/64,2001:db8:1:3::/64" --allowed-signup-email-domains "example.com,anotherexample.com" --bedrock-region "us-west-2" --version "v3"
```

- After about 35 minutes, you will get the following output, which you can access from your browser

```
Frontend URL: https://xxxxxxxxx.cloudfront.net
```

![](./docs/imgs/signin.png)

The sign-in screen will appear as shown above. Self sign-up is off, so create the first user and make them an administrator. The user pool ID is the `AuthUserPoolId...` output of `BedrockChatStack` in the deployment region; Cognito emails a temporary password.

```sh
aws cognito-idp admin-create-user --user-pool-id <user-pool-id> --username user@example.com \
  --desired-delivery-mediums EMAIL --user-attributes Name=email,Value=user@example.com Name=email_verified,Value=true
aws cognito-idp admin-add-user-to-group --user-pool-id <user-pool-id> --username user@example.com --group-name Admin
```

> [!Important]
> Self sign-up is disabled by default. If you enable it with `--enable-self-register`, anyone who knows the URL can sign up, so also restrict IP addresses (`--ipv4-ranges`, `--ipv6-ranges`) and email domains (`--allowed-signup-email-domains`).

> [!TIP]
> If the `Frontend URL` does not appear or Bedrock Chat does not work properly, it may be a problem with the latest version. In this case, please add `--version "v3.0.0"` to the parameters and try deployment again.

## Architecture

It's an architecture built on AWS managed services, eliminating the need for infrastructure management. Utilizing Amazon Bedrock, there's no need to communicate with APIs outside of AWS. This enables deploying scalable, reliable, and secure applications.

- [Amazon DynamoDB](https://aws.amazon.com/dynamodb/): NoSQL database for conversation history storage
- [Amazon API Gateway](https://aws.amazon.com/api-gateway/) + [AWS Lambda](https://aws.amazon.com/lambda/): Backend API endpoint ([AWS Lambda Web Adapter](https://github.com/awslabs/aws-lambda-web-adapter), [FastAPI](https://fastapi.tiangolo.com/))
- [Amazon CloudFront](https://aws.amazon.com/cloudfront/) + [S3](https://aws.amazon.com/s3/): Frontend application delivery ([React](https://react.dev/), [Tailwind CSS](https://tailwindcss.com/))
- [AWS WAF](https://aws.amazon.com/waf/): IP address restriction
- [Amazon Cognito](https://aws.amazon.com/cognito/): User authentication
- [Amazon Bedrock](https://aws.amazon.com/bedrock/): Managed service to utilize foundational models via APIs
- [Amazon Bedrock Knowledge Bases](https://aws.amazon.com/bedrock/knowledge-bases/): Provides a managed interface for Retrieval-Augmented Generation ([RAG](https://aws.amazon.com/what-is/retrieval-augmented-generation/)), offering services for embedding and parsing documents
- [Amazon EventBridge Pipes](https://aws.amazon.com/eventbridge/pipes/): Receiving deletion event of bots from DynamoDB stream and delete CloudFormation stack related to the bot
- [AWS Step Functions](https://aws.amazon.com/step-functions/): Orchestrating ingestion pipeline to embed external knowledge into Bedrock Knowledge Bases
- [Amazon OpenSearch Serverless](https://aws.amazon.com/opensearch-service/features/serverless/): Serves as the backend database for Bedrock Knowledge Bases, providing full-text search and vector search capabilities, enabling accurate retrieval of relevant information
- [Amazon Athena](https://aws.amazon.com/athena/): Query service to analyze S3 bucket

![](docs/imgs/arch.png)

## Deploy using CDK

Super-easy Deployment uses [AWS CodeBuild](https://aws.amazon.com/codebuild/) to perform deployment by CDK internally. This section describes the procedure for deploying directly with CDK.

- Please have UNIX, Docker and a Node.js 22 runtime environment.

> [!Important]
> If there is insufficient storage space in the local environment during deployment, CDK bootstrapping may result in an error. We recommend expanding the volume size of the instance before deploying.

- Clone this repository. The URL below is the upstream project; use this fork's URL to deploy this fork.

```
git clone https://github.com/aws-samples/bedrock-chat
```

- Install npm packages

```
cd bedrock-chat
cd cdk
npm ci
```

- If necessary, edit the following entries in [cdk.json](./cdk/cdk.json).

  - `bedrockRegion`: Region where Bedrock is available. **NOTE: Bedrock does NOT support all regions for now.**
  - `allowedIpV4AddressRanges`, `allowedIpV6AddressRanges`: Allowed IP Address range.
  - `enableLambdaSnapStart`: Defaults to true. Set to false if deploying to a [region that doesn't support Lambda SnapStart for Python functions](https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html#snapstart-supported-regions).
  - `globalAvailableModels`: Defaults to all. If set (list of model IDs), allows to globally control which models appear in dropdown menus across chats for all users and during bot creation in the Bedrock Chat application.
  - `logoPath`: Relative path under `frontend/public` that points to the image displayed at the top of the application drawer.
    The following model IDs are supported (please make sure that they are also enabled in the Bedrock console under Model access in your deployment region):

- **Claude Models:** `claude-v4.5-opus`, `claude-v4.6-opus`, `claude-v4.7-opus`, `claude-v4.8-opus`, `claude-v5-opus`, `claude-v5.5-opus`, `claude-v4.5-sonnet`, `claude-v4.6-sonnet`, `claude-v5-sonnet`, `claude-v5.5-sonnet`, `claude-v4.5-haiku`, `claude-v5.5-haiku`
- **OpenAI Models:** `gpt-5.5`, `gpt-5.6-luna`, `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-6-astra`, `gpt-6-luna`, `gpt-6-sol`, `gpt-6.1-sol`, `gpt-oss-20b`, `gpt-oss-120b`
- **Amazon Nova Models:** `amazon-nova-pro`, `amazon-nova-lite`, `amazon-nova-micro`, `amazon-nova-2-lite`
- **Mistral Models:** `mistral-large`, `mistral-large-2`
- **DeepSeek Models:** `deepseek-r1`
- **Meta Llama Models:** `llama3-3-70b-instruct`

Model availability differs by region. The parameters sent to each model are defined in [model_registry.py](./backend/app/model_registry.py). Models that Amazon Bedrock no longer offers (Claude 3.x, Claude Opus 4, Opus 4.1 and Sonnet 4, Llama 3.2, Mistral 7B and Mixtral 8x7B) are kept only so that existing conversations remain readable, and cannot be selected.

- Before deploying the CDK, you will need to work with Bootstrap once for the region you are deploying to.

```
npx cdk bootstrap
```

- Deploy this sample project

```
npx cdk deploy --require-approval never --all
```

- You will get output similar to the following. The URL of the web app will be output in `BedrockChatStack.FrontendURL`, so please access it from your browser.

```sh
 ✅  BedrockChatStack

✨  Deployment time: 78.57s

Outputs:
BedrockChatStack.AuthUserPoolClientIdXXXXX = xxxxxxx
BedrockChatStack.AuthUserPoolIdXXXXXX = ap-northeast-1_XXXX
BedrockChatStack.BackendApiBackendApiUrlXXXXX = https://xxxxx.execute-api.ap-northeast-1.amazonaws.com
BedrockChatStack.FrontendURL = https://xxxxx.cloudfront.net
```

### Defining Parameters

You can define parameters for your deployment in two ways: using `cdk.json` or using the type-safe `parameter.ts` file.

#### Using cdk.json (Traditional Method)

The traditional way to configure parameters is by editing the `cdk.json` file. This approach is simple but lacks type checking:

```json
{
  "app": "npx ts-node --prefer-ts-exts bin/bedrock-chat.ts",
  "context": {
    "bedrockRegion": "us-east-1",
    "allowedIpV4AddressRanges": ["0.0.0.0/1", "128.0.0.0/1"],
    "selfSignUpEnabled": false,
    "globalAvailableModels": [
      "claude-v5.5-sonnet",
      "claude-v5.5-haiku",
      "amazon-nova-pro",
      "amazon-nova-lite",
      "llama3-3-70b-instruct"
    ]
  }
}
```

To keep deployment-specific values out of Git, pass them with `-c` when you deploy. Command-line context overrides `cdk.json`; values in `cdk.context.json` do not:

```sh
npx cdk deploy --all -c bedrockRegion=ap-northeast-2
```

Numeric parameters accept numbers given with `-c` (for example `-c apiThrottleRateLimit=1000`), and boolean parameters accept `true` and `false`. Lists and objects, such as `allowedIpV4AddressRanges`, must be set in `cdk.json` or with `--cdk-json-override`.

#### Using parameter.ts (Recommended Type-Safe Method)

For better type safety and developer experience, you can use the `parameter.ts` file to define your parameters:

```typescript
// Define parameters for the default environment
bedrockChatParams.set("default", {
  bedrockRegion: "us-east-1",
  allowedIpV4AddressRanges: ["192.168.0.0/16"],
  selfSignUpEnabled: false,
  globalAvailableModels: [
    "claude-v5.5-sonnet",
    "claude-v5.5-haiku",
    "amazon-nova-pro",
    "amazon-nova-lite",
    "llama3-3-70b-instruct",
  ],
});

// Define parameters for additional environments
bedrockChatParams.set("dev", {
  bedrockRegion: "us-west-2",
  allowedIpV4AddressRanges: ["10.0.0.0/8"],
  enableRagReplicas: false, // Cost-saving for dev environment
  enableBotStoreReplicas: false, // Cost-saving for dev environment
});

bedrockChatParams.set("prod", {
  bedrockRegion: "us-east-1",
  allowedIpV4AddressRanges: ["172.16.0.0/12"],
  enableLambdaSnapStart: true,
  enableRagReplicas: true, // Enhanced availability for production
  enableBotStoreReplicas: true, // Enhanced availability for production
});
```

> [!Note]
> Existing users can continue using `cdk.json` without any changes. The `parameter.ts` approach is recommended for new deployments or when you need to manage multiple environments.

### Deploying Multiple Environments

You can deploy multiple environments from the same codebase using the `parameter.ts` file and the `-c envName` option.

#### Prerequisites

1. Define your environments in `parameter.ts` as shown above
2. Each environment will have its own set of resources with environment-specific prefixes

#### Deployment Commands

To deploy a specific environment:

```bash
# Deploy the dev environment
npx cdk deploy --all -c envName=dev

# Deploy the prod environment
npx cdk deploy --all -c envName=prod
```

If no environment is specified, the "default" environment is used:

```bash
# Deploy the default environment
npx cdk deploy --all
```

#### Important Notes

1. **Stack Naming**:

   - The main stacks for each environment will be prefixed with the environment name (e.g., `dev-BedrockChatStack`, `prod-BedrockChatStack`)
   - The shared knowledge base stack is also prefixed (e.g., `dev-BrChatSharedKbStack`); the default environment keeps `BrChatSharedKbStack`
   - However, custom bot stacks (`BrChatKbStack*`) and API publishing stacks (`ApiPublishmentStack*`) do not receive environment prefixes as they are created dynamically at runtime

2. **Resource Naming**:

   - Only some resources receive environment prefixes in their names (e.g., `dev_ddb_export` table, `dev-FrontendWebAcl`)
   - Most resources maintain their original names but are isolated by being in different stacks

3. **Environment Identification**:

   - All resources are tagged with a `CDKEnvironment` tag containing the environment name
   - You can use this tag to identify which environment a resource belongs to
   - Example: `CDKEnvironment: dev` or `CDKEnvironment: prod`

4. **Default Environment Override**: If you define a "default" environment in `parameter.ts`, it will override the settings in `cdk.json`. To continue using `cdk.json`, don't define a "default" environment in `parameter.ts`.

5. **Environment Requirements**: To create environments other than "default", you must use `parameter.ts`. The `-c envName` option alone is not sufficient without corresponding environment definitions.

6. **Resource Isolation**: Each environment creates its own set of resources, allowing you to have development, testing, and production environments in the same AWS account without conflicts.

## Others

### Remove resources

Delete the resources that the application created at runtime first, because they keep billing and `cdk destroy` does not know about them: delete every bot with a knowledge base and every published API in the app, or delete the stacks in [CloudFormation](https://console.aws.amazon.com/cloudformation/home): `BrChatKbStack*` and `BrChatSharedKbStack` (`<envPrefix>-BrChatSharedKbStack` in a named environment) in the Bedrock region, and `ApiPublishmentStack*` in the deployment region.

Then run `npx cdk destroy --all` in `cdk`. Without the CDK, delete `BedrockChatStack`, `BedrockRegionResourcesStack` and `FrontendWafStack` in CloudFormation. Please note that `FrontendWafStack` is in `us-east-1` region.

The conversation and bot tables, the Cognito user pool, the document bucket and the large message bucket are retained so that user data is not lost. To delete them as well, turn off deletion protection on the tables and the user pool, empty the buckets, and delete them in the console or with the AWS CLI.

### Language Settings

This asset automatically detects the language using [i18next-browser-languageDetector](https://github.com/i18next/i18next-browser-languageDetector). You can switch languages from the application menu. Alternatively, you can use Query String to set the language as shown below.

> `https://example.com?lng=ja`

Errors that the backend returns with a known code are shown translated. Other errors show the backend's English message when the language is English, and a translated generic message otherwise.

### Disable self sign up

Self sign up is disabled by default, so administrators create users in the Cognito user pool and the sign-in page has no sign-up tab. To let anyone who can reach the URL create an account, set `selfSignUpEnabled` to `true` in [cdk.json](./cdk/cdk.json). If you configure [external identity provider](#external-identity-provider), the value is ignored, but anyone the provider accepts can sign in; see that section.

### Restrict Domains for Sign-Up Email Addresses

By default, this sample does not restrict the domains for sign-up email addresses. To allow sign-ups only from specific domains, open `cdk.json` and specify the domains as a list in `allowedSignUpEmailDomains`.

```ts
"allowedSignUpEmailDomains": ["example.com"],
```

### External Identity Provider

This sample supports external identity provider. Currently we support [Google](./docs/idp/SET_UP_GOOGLE.md) and [custom OIDC provider](./docs/idp/SET_UP_CUSTOM_OIDC.md).

> [!Important]
> The provider decides who can sign in: every account it authenticates gets a user, which also joins the groups in `autoJoinUserGroups` if you set any. Restrict the provider (for example, an internal Google OAuth app) or set [`allowedSignUpEmailDomains`](#restrict-domains-for-sign-up-email-addresses).

### Optional Frontend WAF

For CloudFront distributions, AWS WAF WebACLs must be created in the us-east-1 region. In some organizations, creating resources outside the primary region is restricted by policy. In such environments, CDK deployment can fail when attempting to provision the Frontend WAF in us-east-1.

To accommodate these restrictions, the Frontend WAF stack is optional. When disabled, the CloudFront distribution is deployed without a WebACL. This means you won’t have IP allow/deny controls at the frontend edge. Authentication and all other application controls continue to work as usual. Note that this setting only affects the Frontend WAF (CloudFront scope); the Published API WAF (regional) remains unaffected.

To disable the Frontend WAF set the following in `parameter.ts` (Recommended Type-Safe Method):

```ts
bedrockChatParams.set("default", {
  enableFrontendWaf: false,
});
```

Or if using the legacy `cdk/cdk.json` set the following:

```json
"enableFrontendWaf": false
```

### Add new users to groups automatically

This sample has the following groups to give permissions to users:

- [`Admin`](./docs/ADMINISTRATOR.md)
- [`CreatingBotAllowed`](#bot-personalization--bot-store)
- [`PublishAllowed`](./docs/PUBLISH_API.md)

If you want newly created users to automatically join groups, you can specify them in [cdk.json](./cdk/cdk.json).

```json
"autoJoinUserGroups": ["CreatingBotAllowed"],
```

By default, new users join no group, because members of `CreatingBotAllowed` can create bots with dedicated knowledge bases, which cost money (see [Limit dedicated knowledge bases](#limit-dedicated-knowledge-bases)). Add users to groups in Cognito, or list the groups here.

### Configure RAG Replicas

`enableRagReplicas` is an option in [cdk.json](./cdk/cdk.json) that controls the replica settings for the RAG database, specifically the Knowledge Bases using Amazon OpenSearch Serverless.

- **Default**: true
- **true**: Enhances availability by enabling additional replicas, making it suitable for production environments but increasing costs.
- **false**: Reduces costs by using fewer replicas, making it suitable for development and testing.

This is an account/region-level setting, affecting the entire application rather than individual bots.

> [!Note]
> As of June 2024, Amazon OpenSearch Serverless supports 0.5 OCU, lowering entry costs for small-scale workloads. Production deployments can start with 2 OCUs, while dev/test workloads can use 1 OCU. OpenSearch Serverless automatically scales based on workload demands. For more detail, visit [announcement](https://aws.amazon.com/jp/about-aws/whats-new/2024/06/amazon-opensearch-serverless-entry-cost-half-collection-types/).

### Configure Bot Store

The bot store feature allows users to share and discover custom bots. You can configure the bot store through the following settings in [cdk.json](./cdk/cdk.json):

```json
{
  "context": {
    "enableBotStore": true,
    "enableBotStoreReplicas": false,
    "botStoreLanguage": "en"
  }
}
```

- **enableBotStore**: Controls whether the bot store feature is enabled (default: `true`). The bot store runs two OpenSearch Ingestion pipelines and an OpenSearch Serverless collection continuously, which incurs a baseline cost even when idle.
- **botStoreLanguage**: Sets the primary language for bot search and discovery (default: `"en"`). This affects how bots are indexed and searched in the bot store, optimizing text analysis for the specified language.
- **enableBotStoreReplicas**: Controls whether standby replicas are enabled for the OpenSearch Serverless collection used by bot store (default: `false`). Setting it to `true` improves availability but increases costs, while `false` reduces costs but may affect availability.
  > **Important**: You can't update this property after the collection is already created. If you attempt to modify this property, the collection continues to use the original value.

### Cross-region and Global inference

[Cross-region and Global inference](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles-support.html)
allows Amazon Bedrock to dynamically route model inference requests across
multiple AWS regions, enhancing throughput and resilience during peak demand
periods. Global inference routes the requests to the optimal region based on
latency and availability anywhere in the world, while cross-region inference
routes requests within the same AWS region, for example, within the US. Some
SCPs may restrict on or the other or both and therefore you can configure them
independently. By default both are enabled.

To configure change the following settings in `cdk.json` or `parameter.ts`:

```json
"enableBedrockGlobalInference": false,
"enableBedrockCrossRegionInference": false,
```

### Configure Default Models

By default, the application uses `claude-v5.5-sonnet` as the default model for new chat conversations and `claude-v5.5-haiku` for generating conversation titles and summarizing internet search results. However, some AWS accounts may not have access to these specific models, or you may prefer to use different models as defaults.

You can configure the default models using the following parameters in `parameter.ts`:

```typescript
bedrockChatParams.set("default", {
  // Model selected by default when users start a new chat
  defaultModel: "claude-v5.5-sonnet",
  
  // Model used for generating conversation titles (cost optimization)
  titleModel: "claude-v5.5-haiku",
});
```

- **defaultModel** (optional): The model pre-selected in the chat UI when users start a new conversation. If not set, defaults to `claude-v5.5-sonnet`.
- **titleModel** (optional): The model used to automatically generate conversation titles. If not set, falls back to `defaultModel`, then to `claude-v5.5-haiku`.

**When to configure these settings:**

- Your AWS account doesn't have access to the default models (`claude-v5.5-sonnet` or `claude-v5.5-haiku`)
- You want to use a different model as the default for your users
- You want to optimize costs by using a cheaper model (like `claude-v5.5-haiku` or `amazon-nova-lite`) for title generation
- You want to use the same model for both chat and title generation for consistency

> [!Note]
> The `titleModel` is only used internally for generating short conversation titles. Using a smaller, cheaper model for this purpose is recommended as it reduces costs without affecting the user's chat experience.

### Alarms and API Throttling

CloudWatch alarms notify an SNS topic (output `AlarmTopicArn`) when:

- the REST API answers with server errors (5xx);
- generating chat answers fails repeatedly;
- the WebSocket chat Lambda fails, for example with a timeout or out of memory;
- Lambda concurrency limits throttle chat requests (these are not the API Gateway 429 responses caused by `apiThrottleRateLimit`);
- the knowledge sync state machine fails, times out or is aborted, or a bot's knowledge sync fails;
- the resources of a deleted bot could not be removed;
- a day of chat answers costs more than `dailyChatCostAlarmUsd` (default 100 USD; 0 turns it off). The cost is computed with the model prices in the backend and includes published APIs;
- a published API fails to answer or its Lambda functions fail. These alarms are in each `ApiPublishmentStack*` stack ([API publication](./docs/PUBLISH_API.md#architecture)).

Set `alarmEmail` to subscribe an email address; AWS sends a confirmation email first.

The REST and WebSocket APIs are limited to `apiThrottleRateLimit` requests per second (default 500) with a burst of `apiThrottleBurstLimit` (default 1000). Raise them for large deployments. The WebSocket API rejects connections at `$connect` unless they pass a valid Cognito ID token.

```typescript
bedrockChatParams.set("default", {
  alarmEmail: "ops@example.com",
  apiThrottleRateLimit: 500,
  apiThrottleBurstLimit: 1000,
});
```

> [!Important]
> Defining the `default` environment in `parameter.ts` replaces every setting in `cdk.json`, including IP restrictions. To change a single setting, add it to `cdk.json` or pass it on the command line instead, for example `npx cdk deploy --all -c alarmEmail=ops@example.com`, or `./bin.sh --cdk-json-override '{"context":{"alarmEmail":"ops@example.com"}}'`. `-c` works for strings, numbers and `true`/`false`; set lists and objects in `cdk.json` or with `--cdk-json-override`.

### Limit dedicated knowledge bases

Each bot with its own (dedicated) knowledge base has an OpenSearch Serverless collection that is billed while the bot exists. `maxDedicatedKnowledgeBasesPerUser` (default 2) limits how many such bots a user can own; 0 removes the limit, and administrators are not limited. Bots that use a shared or an existing knowledge base do not count.

```json
"maxDedicatedKnowledgeBasesPerUser": 2
```

### Usage analysis retention

The DynamoDB exports used for [usage analysis](./docs/ADMINISTRATOR.md#notes) and the Athena query results are deleted after `usageAnalysisRetentionDays` (default 90).

```json
"usageAnalysisRetentionDays": 90
```

### Lambda SnapStart

[Lambda SnapStart](https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html) improves cold start times for Lambda functions, providing faster response times for better user experience. On the other hand, for Python functions, there is a [charge depending on cache size](https://aws.amazon.com/lambda/pricing/#SnapStart_Pricing) and [not available in some regions](https://docs.aws.amazon.com/lambda/latest/dg/snapstart.html#snapstart-supported-regions) currently. To disable SnapStart, edit `cdk.json`.

```json
"enableLambdaSnapStart": false
```

### Configure Custom Domain

You can configure a custom domain for the CloudFront distribution by setting the following parameters in [cdk.json](./cdk/cdk.json):

```json
{
  "alternateDomainName": "chat.example.com",
  "hostedZoneId": "Z0123456789ABCDEF"
}
```

- `alternateDomainName`: The custom domain name for your chat application (e.g., chat.example.com)
- `hostedZoneId`: The ID of your Route 53 hosted zone where the domain records will be created

When these parameters are provided, the deployment will automatically:

- Create an ACM certificate with DNS validation in us-east-1 region
- Create the necessary DNS records in your Route 53 hosted zone
- Configure CloudFront to use your custom domain

> [!Note]
> The domain must be managed by Route 53 in your AWS account. The hosted zone ID can be found in the Route 53 console.

### Configure allowed countries (geo restriction)

You can restrict access to Bedrock-Chat based on the country the client is accessing it from.
Use the `allowedCountries` parameter in [cdk.json](./cdk/cdk.json) which takes a list of [ISO-3166 Country Codes](https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes).
For example a New Zealand based business may decide that only IP addresses from New Zealand (NZ) and Australia (AU) can access the portal and everyone else should be denied access.
To configure this behaviour use the following setting in [cdk.json](./cdk/cdk.json):

```json
{
  "allowedCountries": ["NZ", "AU"]
}
```

Or, using `parameter.ts` (Recommended Type-Safe Method):

```ts
// Define parameters for the default environment
bedrockChatParams.set("default", {
  allowedCountries: ["NZ", "AU"],
});
```

### Disable IPv6 support

The frontend gets both IP and IPv6 addresses by default. In some rare
circumstances, you may need to disable IPv6 support explicitly. To do this, set
the following parameter in [parameter.ts](./cdk/parameter.ts) or similarly in [cdk.json](./cdk/cdk.json):

```ts
"enableFrontendIpv6": false
```

If left unset the IPv6 support will be enabled by default.

### Local Development

See [LOCAL DEVELOPMENT](./docs/LOCAL_DEVELOPMENT.md).

### Contribution

Thank you for considering contributing to this repository! We welcome bug fixes, language translations (i18n), feature enhancements, [agent tools](./docs/AGENT.md#how-to-develop-your-own-tools), and other improvements.

For feature enhancements and other improvements, **before creating a Pull Request, we would greatly appreciate it if you could create a Feature Request Issue to discuss the implementation approach and details. For bug fixes and language translations (i18n), proceed with creating a Pull Request directly.**

Please also take a look at the following guidelines before contributing:

- [Local Development](./docs/LOCAL_DEVELOPMENT.md)
- [CONTRIBUTING](./CONTRIBUTING.md)

## Contacts

- [Takehiro Suzuki](https://github.com/statefb)
- [Yusuke Wada](https://github.com/wadabee)
- [Yukinobu Mine](https://github.com/Yukinobu-Mine)

## 🏆 Significant Contributors

- [fsatsuki](https://github.com/fsatsuki)
- [k70suK3-k06a7ash1](https://github.com/k70suK3-k06a7ash1)

## Contributors

[![bedrock chat contributors](https://contrib.rocks/image?repo=aws-samples/bedrock-chat&max=1000)](https://github.com/aws-samples/bedrock-chat/graphs/contributors)

## License

This library is licensed under the MIT-0 License. See [the LICENSE file](./LICENSE).
