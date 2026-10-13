# Local development

## Backend Development

See [backend/README](../backend/README.md).

## Frontend Development

In this sample, you can locally modify and launch the frontend using AWS resources (`API Gateway`, `Cognito`, etc.) that have been deployed with `npx cdk deploy`.

1. Refer to [Deploy using CDK](../README.md#deploy-using-cdk) for deploying on the AWS environment.
2. Copy the `frontend/.env.template` and save it as `frontend/.env.local`.
3. Fill in the contents of `.env.local` based on the output results of `npx cdk deploy` (such as `BedrockChatStack.AuthUserPoolClientIdXXXXX`).
4. Execute the following command:

```zsh
cd frontend && npm ci && npm run dev
```

The dev server must run on port 5173 (the Vite default): `http://localhost:5173` is the only local origin that the deployed API allows for CORS.

Streaming responses are served by the WebSocket API Lambda, which cannot run locally. Set `VITE_APP_WS_ENDPOINT` to the deployed WebSocket endpoint (`BedrockChatStack.WebSocketWebSocketEndpoint...` in the stack outputs), or set `VITE_APP_USE_STREAMING` to `false` to use the REST API without streaming.

## Tests

```sh
cd backend && poetry run pytest          # unit tests, no AWS access
cd frontend && npx vitest run            # unit tests
cd cdk && npm test                       # infrastructure tests
```

Backend tests that call AWS are marked with `aws` and excluded by default. See [backend/README](../backend/README.md#tests).

## Pre-commit hook

Run `lefthook install` in the repository root to check staged files on commit. See [CONTRIBUTING](../CONTRIBUTING.md#contributing-via-pull-requests) for `lefthook run check`, which runs the main CI checks.
