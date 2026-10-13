# Backend API

Written in Python with [FastAPI](https://fastapi.tiangolo.com/).

## Getting started

- To get started, we need to deploy resources to create DynamoDB / Bedrock resource. To deploy, please see [Deploy using CDK](../README.md#deploy-using-cdk).
- Create [poetry](https://python-poetry.org/) environment on your local machine

```sh
# Python 3.13 or later
cd backend
python3 -m venv .venv  # Optional (If you don't want to install poetry on your env)
source .venv/bin/activate  # Optional (If you don't want to install poetry on your env)
pip install poetry
poetry install
```

- Configure environment variables

```sh
export CONVERSATION_TABLE_NAME=BedrockChatStack-DatabaseConversationTableV3xxxx
export BOT_TABLE_NAME=BedrockChatStack-DatabaseBotTableV3xxxx
export ACCOUNT=yyyy
export REGION=ap-northeast-1
export BEDROCK_REGION=us-east-1
export DOCUMENT_BUCKET=bedrockchatstack-documentbucketxxxxxxx
export LARGE_MESSAGE_BUCKET=bedrockchatstack-largemessagebucketxxx
export USER_POOL_ID=xxxxxxxxx
export CLIENT_ID=xxxxxxxxx
export OPENSEARCH_DOMAIN_ENDPOINT=https://abcdefghijklmnopqrst.aa-region-1.aoss.amazonaws.com
```

  Optional variables:

  - `LOG_LEVEL`: level of the `app` loggers (default `INFO`).
  - `ENABLE_BEDROCK_GLOBAL_INFERENCE`, `ENABLE_BEDROCK_CROSS_REGION_INFERENCE`: `true` to use inference profiles.
  - `GLOBAL_AVAILABLE_MODELS`: JSON array of model names users may choose. Empty means all models.
  - `DEFAULT_MODEL`, `TITLE_MODEL`: model names for new conversations and title generation.
  - `EMBEDDING_STATE_MACHINE_ARN`: the embedding state machine, needed to sync bot knowledge.
  - `MAX_DEDICATED_KNOWLEDGE_BASES_PER_USER`: how many bots with a dedicated knowledge base a user may own (default `0`, unlimited).
  - `METRICS_NAMESPACE`: CloudWatch namespace of the chat cost metric (default `BedrockChat`).

- Configure CDK configration.
Local development requires OpenSearch data access permissions for the IAM role to be used. You can set this parameter in either `cdk/cdk.json` or `cdk/parameter.ts`.

  This configuration grants the following permissions:

  For the OpenSearch Collection:

    ```
    "aoss:DescribeCollectionItems",
    "aoss:CreateCollectionItems", 
    "aoss:DeleteCollectionItems",
    "aoss:UpdateCollectionItems"
    ```

  For the index:

    ```
    "aoss:DescribeIndex", 
    "aoss:ReadDocument", 
    "aoss:WriteDocument",
    "aoss:CreateIndex",
    "aoss:DeleteIndex",
    "aoss:UpdateIndex"
    ```

  Example in cdk/cdk.json:
    ```
    json 

    {
      "devAccessIamRoleArn": "arn:aws:iam::123456789012:role/<role name>"
    }
    ```

## Launch local server

```sh
poetry run uvicorn app.main:app  --reload --host 0.0.0.0 --port 8000
```

- To refer the specification, access to [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for [Swagger](https://swagger.io/) and [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) for [Redoc](https://github.com/Redocly/redoc).

## Tests

Unit tests run without AWS access and are executed in CI:

```sh
poetry run pytest
```

Tests marked `aws` call real AWS resources (Bedrock, DynamoDB, Cognito, OpenSearch Serverless) and may incur costs. Run them only with credentials for a deployed development stack and the environment variables listed above:

```sh
poetry run pytest -m aws
```

Some of them also need deployed resources or ids from the environment; for example, some create users in the user pool given by `USER_POOL_ID`.

Tests that only need DynamoDB use in-memory tables from [moto](https://github.com/getmoto/moto): add `@pytest.mark.usefixtures("dynamodb_tables")` (see `tests/conftest.py`). Mark a new test with `@pytest.mark.aws` only if it needs other AWS services or internet access.
