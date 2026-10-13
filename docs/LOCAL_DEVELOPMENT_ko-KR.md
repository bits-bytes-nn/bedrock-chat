# 로컬 개발

## 백엔드 개발

[backend/README](../backend/README.md)를 참조하세요.

## 프론트엔드 개발

이 예제에서는 `npx cdk deploy`로 배포된 AWS 리소스(`API Gateway`, `Cognito` 등)를 사용하여 프론트엔드를 로컬에서 수정하고 실행할 수 있습니다.

1. AWS 환경에 배포하는 방법은 [Deploy using CDK](../README.md#deploy-using-cdk)를 참조하세요.
2. `frontend/.env.template`를 복사하여 `frontend/.env.local`로 저장하세요.
3. `npx cdk deploy`의 출력 결과(예: `BedrockChatStack.AuthUserPoolClientIdXXXXX`)를 바탕으로 `.env.local`의 내용을 채우세요.
4. 다음 명령어를 실행하세요:

```zsh
cd frontend && npm ci && npm run dev
```

개발 서버는 Vite 기본값인 5173 포트에서 실행해야 합니다. 배포된 API가 CORS로 허용하는 로컬 출처는 `http://localhost:5173`뿐입니다.

스트리밍 응답은 WebSocket API Lambda가 처리하며, 이 Lambda는 로컬에서 실행할 수 없습니다. `VITE_APP_WS_ENDPOINT`에 배포된 WebSocket 엔드포인트(스택 출력의 `BedrockChatStack.WebSocketWebSocketEndpoint...`)를 지정하거나, `VITE_APP_USE_STREAMING`을 `false`로 설정해 스트리밍 없이 REST API를 사용하세요.

## 테스트

```sh
cd backend && poetry run pytest          # 단위 테스트, AWS 접근 없음
cd frontend && npx vitest run            # 단위 테스트
cd cdk && npm test                       # 인프라 테스트
```

AWS를 호출하는 백엔드 테스트에는 `aws` 마커가 붙어 있으며 기본 실행에서 제외됩니다. 자세한 내용은 [backend/README](../backend/README.md#tests)를 참고하세요.

## pre-commit 훅

저장소 루트에서 `lefthook install`을 실행하면 커밋할 때 스테이징한 파일을 검사합니다. 주요 CI 검사를 실행하는 `lefthook run check`는 [CONTRIBUTING](../CONTRIBUTING.md#contributing-via-pull-requests)을 참고하세요.
