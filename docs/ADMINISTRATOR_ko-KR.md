# 관리 기능

## 전제 조건

관리자 사용자는 관리 콘솔 > Amazon Cognito 사용자 풀 또는 aws cli를 통해 설정할 수 있는 `Admin`이라는 그룹의 멤버여야 합니다. 사용자 풀 ID는 CloudFormation > BedrockChatStack > Outputs > `AuthUserPoolIdxxxx`를 통해 확인할 수 있습니다.

![](./imgs/group_membership_admin.png)

## 공개 봇을 필수 봇으로 표시하기

관리자는 공개 봇을 "필수"로 표시할 수 있습니다. 필수로 표시된 봇은 봇 스토어의 "필수" 섹션에 표시되어 사용자가 쉽게 접근할 수 있습니다. 이를 통해 관리자는 모든 사용자가 사용하기를 원하는 중요한 봇을 고정할 수 있습니다.

### 예시

- HR 도우미 봇: 직원들의 인사 관련 질문과 업무를 지원합니다.
- IT 지원 봇: 내부 기술 문제와 계정 관리에 대한 지원을 제공합니다.
- 내부 정책 안내 봇: 출근 규정, 보안 정책 및 기타 내부 규정에 대한 자주 묻는 질문에 답변합니다.
- 신입 직원 온보딩 봇: 신입 사원의 첫 출근일에 절차와 시스템 사용법을 안내합니다.
- 복리후생 정보 봇: 회사의 복리후생 프로그램과 welfare 서비스에 대해 설명합니다.

![](./imgs/admin_bot_menue.png)
![](./imgs/bot_store.png)

## 피드백 루프

LLM의 출력이 항상 사용자의 기대에 부합하지는 않습니다. 때로는 사용자의 요구사항을 충족시키지 못할 수 있습니다. LLM을 비즈니스 운영과 일상생활에 효과적으로 "통합"하기 위해서는 피드백 루프를 구현하는 것이 필수적입니다. Bedrock Chat은 사용자가 불만족이 발생한 이유를 분석할 수 있도록 설계된 피드백 기능을 갖추고 있습니다. 분석 결과를 바탕으로 프롬프트, RAG 데이터 소스, 매개변수 등을 적절히 조정할 수 있습니다.

![](./imgs/feedback_loop.png)

![](./imgs/feedback-using-claude-chat.png)

데이터 분석가들은 [Amazon Athena](https://aws.amazon.com/jp/athena/)를 사용하여 대화 로그에 접근할 수 있습니다. [Jupyter Notebook](https://jupyter.org/)으로 데이터를 분석하고자 하는 경우, [이 노트북 예제](../examples/notebooks/feedback_analysis_example.ipynb)를 참고할 수 있습니다.

## 대시보드

현재 공개 봇 사용량의 기본 개요를 제공합니다. 지정한 기간의 데이터를 봇별로 집계하고 사용 요금순으로 정렬합니다.

![](./imgs/admin_bot_analytics.png)

## 참고사항

- [아키텍처](../README.md#architecture)에 명시된 대로, 관리자 기능은 DynamoDB에서 내보낸 S3 버킷을 참조합니다. 내보내기는 1시간마다 수행되므로 최근 대화는 즉시 반영되지 않을 수 있습니다.

- 내보낸 데이터에는 사용자가 삭제한 대화를 포함해 대화 전문이 들어 있습니다. 내보낸 데이터는 `usageAnalysisRetentionDays`(기본값 90일)가 지나면 삭제되므로 사용량 분석도 이 기간만 다룹니다. 버킷과 Athena에 대한 접근 권한을 그에 맞게 제한하세요.

- `BedrockChatStack`의 `TableAccessRole`은 대화 테이블과 봇 테이블을 읽고 씁니다. 이 역할은 IAM 경로 `/bedrock-chat/<env>/`(기본 환경은 `default`) 아래의 역할과, 이 스택 또는 `ApiPublishmentStack*` 이름으로 시작하는 역할만 신뢰합니다. 따라서 역할을 만들 수 있는 권한은 테이블 접근 권한만큼 민감합니다.

- 공개 봇 사용량에서는 지정된 기간 동안 전혀 사용되지 않은 봇은 목록에 표시되지 않습니다.

> [!Important]
> 여러 환경(dev, prod 등)을 사용하는 경우, Athena 데이터베이스 이름에 환경 접두사가 포함됩니다. `bedrockchatstack_usage_analysis` 대신 다음과 같이 됩니다:
>
> - 기본 환경의 경우: `bedrockchatstack_usage_analysis`
> - 지정된 환경의 경우: `<env-prefix>_bedrockchatstack_usage_analysis` (예: `dev_bedrockchatstack_usage_analysis`)
>
> 또한 테이블 이름에도 환경 접두사가 포함됩니다:
>
> - 기본 환경의 경우: `ddb_export`
> - 지정된 환경의 경우: `<env-prefix>_ddb_export` (예: `dev_ddb_export`)
>
> 여러 환경에서 작업할 때는 쿼리를 적절히 조정해야 합니다.

## 대화 데이터 다운로드

Athena에서 SQL을 사용하여 대화 로그를 조회할 수 있습니다. 로그를 다운로드하려면 관리 콘솔에서 Athena 쿼리 편집기를 열고 SQL을 실행하세요. 다음은 사용 사례 분석에 유용한 예제 쿼리들입니다. 피드백은 `MessageMap` 속성에서 참조할 수 있습니다.

### Bot ID별 쿼리

`bot-id`와 `datehour`을 수정하세요. `bot-id`는 왼쪽 사이드바에 표시되는 Bot Publish API에서 접근할 수 있는 Bot 관리 화면에서 확인할 수 있습니다. URL의 끝부분 `https://xxxx.cloudfront.net/admin/bot/<bot-id>`을 참고하세요.

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
> 명명된 환경(예: "dev")을 사용하는 경우, 위 쿼리에서 `bedrockchatstack_usage_analysis.ddb_export`를 `dev_bedrockchatstack_usage_analysis.dev_ddb_export`로 대체하세요.

### 사용자 ID별 쿼리

`user-id`와 `datehour`을 수정하세요. `user-id`는 Bot 관리 화면에서 확인할 수 있습니다.

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
> 명명된 환경(예: "dev")을 사용하는 경우, 위 쿼리에서 `bedrockchatstack_usage_analysis.ddb_export`를 `dev_bedrockchatstack_usage_analysis.dev_ddb_export`로 대체하세요.

## 업그레이드

README의 [Upgrading an Existing Deployment](../README.md#upgrading-an-existing-deployment)도 함께 참고하세요.

`npx cdk deploy --all`로 기존 배포를 그대로 업데이트합니다. DynamoDB는 테이블을 한 번 업데이트할 때 보조 인덱스를 하나만 추가합니다. 대화 테이블에 글로벌 보조 인덱스가 없다면(DynamoDB 콘솔 > 인덱스) 커밋 `d095ec1`을 먼저 배포한 다음 v3를 배포하세요. upstream v3 배포에는 `SKIndex`가 있으므로 한 번에 업그레이드됩니다.

upstream에서 업그레이드하는 경우:

- 사용량 분석 내보내기 버킷과 Athena 쿼리 결과 버킷에 `usageAnalysisRetentionDays`(기본값 90일) 만료 규칙이 생겨 오래된 내보내기가 삭제됩니다. 먼저 복사해 두거나 값을 늘리세요.
- `CreatingBotAllowed` 그룹의 기존 멤버는 그대로 남습니다. 이전에는 모든 사용자가 이 그룹에 자동으로 가입했으므로(`autoJoinUserGroups`의 기본값은 이제 `[]`) Cognito에서 그룹 멤버를 검토하세요.

게시된 API는 게시할 때의 코드와 스택 설정(기본 스로틀링, 알람, 비용 지표와 지표 네임스페이스)을 그대로 씁니다. 업그레이드한 뒤 다시 게시하세요.

## 지식 동기화 복구

봇의 지식 동기화가 대기 중이거나 실행 중이면 소유자는 봇을 저장할 수 없습니다(오류 코드 `knowledge_base_syncing`과 함께 409). 동기화가 시간 초과되거나 중단되면 봇은 `RUNNING` 상태로 남습니다. 이때 관리자가 봇을 저장하면 새 동기화가 대기열에 들어가며, 소유자는 봇을 삭제할 수 있습니다. 동기화에 실패한 봇은 변경 사항이 없어도 저장하면 동기화를 다시 시도합니다.

동기화 중에도 봇을 삭제할 수 있습니다. 동기화가 끝나면 삭제된 봇을 위해 만든 지식 기반 스택을 삭제합니다. 이 삭제가 실패하면 동기화 상태 업데이트 실패 알람이 울립니다([Alarms and API Throttling](../README.md#alarms-and-api-throttling)). Bedrock 리전에서 봇이 더 이상 없는 `BrChatKbStack*` 스택을 찾아 삭제하세요.

## 사용자 데이터 삭제

Cognito에서 사용자를 삭제해도 그 사용자의 대화와 봇은 삭제되지 않습니다. 이를 삭제하려면 `backend`에서 [delete_user_data.py](../backend/scripts/delete_user_data.py)를 실행하세요. 테이블 이름과 대용량 메시지 버킷은 `BedrockChatStack` 출력에서 확인합니다.

```sh
PYTHONPATH=. CONVERSATION_TABLE_NAME=... BOT_TABLE_NAME=... LARGE_MESSAGE_BUCKET=... REGION=... \
  poetry run python scripts/delete_user_data.py <user-id> [--yes]
```

사용자 ID는 Cognito의 `sub` 속성이며, 외부 ID 공급자로 로그인하는 사용자는 Username과 값이 다릅니다. `--yes`를 지정하지 않으면 삭제할 항목만 보여 줍니다. 봇을 삭제하면 지식 기반 스택, 문서, 게시된 API와 그 API 클라이언트의 대화도 함께 삭제되며, 이 사용자가 공유한 봇은 다른 사용자도 더 이상 쓸 수 없습니다.

이 스크립트는 봇 항목을 직접 삭제하므로, API를 통해 삭제할 때처럼 게시 진행 여부를 확인하지 않습니다. 이 사용자의 봇이 게시 중이 아닐 때 실행하고, 실행한 뒤 CloudFormation에 이 사용자 봇의 `ApiPublishmentStack*` 스택이 남아 있지 않은지 확인하세요.

삭제한 항목은 테이블의 특정 시점 복구(PITR) 백업에 최대 35일 동안 남고, 사용량 분석 내보내기는 `usageAnalysisRetentionDays`가 지나면 만료됩니다. API 게시를 취소해도 클라이언트의 대화는 남으며, 봇을 삭제할 때 함께 삭제됩니다.
