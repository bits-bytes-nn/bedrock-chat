import en from '../en';

const translation: typeof en = {
  translation: {
    signIn: {
      button: {
        login: '로그인',
      },
    },
    app: {
      name: 'Bedrock Chat',
      inputMessage: '무엇을 도와드릴까요?',
      myBots: '내 봇',
      discoverBots: '봇 둘러보기',
      pinnedBots: '고정된 봇',
      starredBots: '즐겨찾기한 봇',
      recentlyUsedBots: '최근 사용한 봇',
      conversationHistory: '최근 대화',
      chatWaitingSymbol: '▍',
      adminConsoles: '관리자 패널',
      backChat: '채팅으로 돌아가기',
      userGroups: '사용자 그룹',
      loading: '불러오는 중...',
      currentModel: '모델: {{model}}',
    },
    model: {
      'claude-v4.8-opus': {
        label: 'Claude 4.8 (Opus)',
        description:
          '복잡한 추론, 코딩, 장시간 실행되는 에이전트 작업에 적합한 Opus 모델입니다.',
      },
      'claude-v5-opus': {
        label: 'Claude 5 (Opus)',
        description:
          '가장 까다로운 추론과 에이전트 작업을 위한 5세대 Opus 모델입니다.',
      },
      'claude-v5.5-opus': {
        label: 'Claude 5.5 (Opus)',
        description:
          '복잡한 추론, 코딩, 장시간 실행되는 에이전트에 적합한 가장 뛰어난 Claude 모델입니다.',
      },
      'claude-v5-sonnet': {
        label: 'Claude 5 (Sonnet)',
        description: '지능, 속도, 비용의 균형을 갖춘 5세대 Sonnet 모델입니다.',
      },
      'claude-v5.5-sonnet': {
        label: 'Claude 5.5 (Sonnet)',
        description:
          '대규모 환경에서도 뛰어난 코딩 및 에이전트 성능을 제공하는 최신 Sonnet 모델입니다.',
      },
      'claude-v5.5-haiku': {
        label: 'Claude 5.5 (Haiku)',
        description:
          '대량 작업에 적합한 가장 빠르고 비용 효율적인 Claude 모델입니다.',
      },
      'gpt-5.5': {
        label: 'GPT-5.5',
        description: '일반 작업을 위한 OpenAI 추론 모델입니다.',
      },
      'gpt-5.6-luna': {
        label: 'GPT-5.6 Luna',
        description: '속도와 비용에 최적화된 OpenAI GPT-5.6 모델입니다.',
      },
      'gpt-5.6-sol': {
        label: 'GPT-5.6 Sol',
        description: '복잡한 추론을 위한 OpenAI GPT-5.6 모델입니다.',
      },
      'gpt-5.6-terra': {
        label: 'GPT-5.6 Terra',
        description: '성능과 비용의 균형을 갖춘 OpenAI GPT-5.6 모델입니다.',
      },
      'gpt-6-astra': {
        label: 'GPT-6 Astra',
        description:
          '가장 까다로운 작업을 위한 OpenAI GPT-6 플래그십 모델입니다.',
      },
      'gpt-6-luna': {
        label: 'GPT-6 Luna',
        description: '속도와 비용에 최적화된 OpenAI GPT-6 모델입니다.',
      },
      'gpt-6-sol': {
        label: 'GPT-6 Sol',
        description: '복잡한 추론을 위한 OpenAI GPT-6 모델입니다.',
      },
      'gpt-6.1-sol': {
        label: 'GPT-6.1 Sol',
        description: '복잡한 추론을 위한 최신 OpenAI GPT-6.1 모델입니다.',
      },
      'amazon-nova-2-lite': {
        label: 'Amazon Nova 2 Lite',
        description:
          '빠른 일상 작업에 적합한 저비용 멀티모달 Amazon Nova 모델입니다.',
      },
      'claude-v4.5-opus': {
        label: 'Claude 4.5 (Opus)',
        description:
          '강력한 추론과 실용적인 성능을 갖추면서도 이전 Opus 모델보다 합리적인 가격으로 이용할 수 있는 고성능 Opus 모델입니다.',
      },
      'claude-v4.6-opus': {
        label: 'Claude 4.6 (Opus)',
        description:
          '더 신중하게 계획하고, 에이전트 작업을 더 오래 지속하며, 100만 토큰 컨텍스트 윈도로 대규모 코드베이스에서도 안정적으로 동작하는 플래그십 모델입니다.',
      },
      'claude-v4.7-opus': {
        label: 'Claude 4.7 (Opus)',
        description:
          '코딩, 엔터프라이즈 워크플로, 장시간 실행되는 에이전트 작업을 위해 설계된 고성능 Opus 모델입니다.',
      },
      'claude-v4.5-sonnet': {
        label: 'Claude 4.5 (Sonnet)',
        description:
          '뛰어난 코딩 성능과 확장된 작업 처리 능력을 갖춘 이전 세대 Sonnet 모델입니다.',
      },
      'claude-v4.6-sonnet': {
        label: 'Claude 4.6 (Sonnet)',
        description:
          '코딩, 컴퓨터 사용, 긴 컨텍스트 추론, 에이전트 계획 능력을 개선하고 100만 토큰 컨텍스트 윈도를 지원하는 전면 업그레이드된 중간 등급 모델입니다.',
      },
      'claude-v4.5-haiku': {
        label: 'Claude 4.5 (Haiku)',
        description:
          '최첨단에 가까운 성능과 확장된 사고(extended thinking) 기능을 갖춘 가장 빠르고 지능적인 Haiku 모델입니다.',
      },
      'mistral-large': {
        label: 'Mistral Large',
        description:
          '상당한 추론 능력이 필요한 복잡한 작업이나 합성 텍스트 생성, 코드 생성처럼 고도로 전문화된 작업에 적합합니다.',
      },
      'mistral-large-2': {
        label: 'Mistral Large2',
        description:
          '수십 개 언어와 80개 이상의 프로그래밍 언어를 지원하고, 네이티브 함수 호출, JSON 출력, 추론 등 동급 최고의 에이전트 기능을 갖춘 고급 LLM입니다.',
      },
      'amazon-nova-pro': {
        label: 'Amazon Nova Pro',
        description:
          '다양한 작업에서 정확도, 속도, 비용의 최적 조합을 제공하는 고성능 멀티모달 모델입니다.',
      },
      'amazon-nova-lite': {
        label: 'Amazon Nova Lite',
        description:
          '이미지, 동영상, 텍스트 입력을 매우 빠르게 처리하는 초저비용 멀티모달 모델입니다.',
      },
      'amazon-nova-micro': {
        label: 'Amazon Nova Micro',
        description:
          'Amazon Nova 모델 제품군 중 가장 낮은 지연 시간의 응답을 매우 저렴한 비용으로 제공하는 텍스트 전용 모델입니다.',
      },
      'deepseek-r1': {
        label: 'DeepSeek R1',
        description:
          '일반 추론, 수학, 과학, 코드 생성에 최적화된 최첨단 추론 모델입니다. 영어와 중국어를 지원합니다.',
      },
      // Meta Llama 3 models
      'llama3-3-70b-instruct': {
        label: 'Meta Llama 3.3 70B Instruct',
        description:
          '더 낮은 비용으로 405B 모델에 준하는 성능을 제공하며, 뛰어난 추론 및 지시 이행 능력을 갖춘 최신 Llama 3 모델입니다.',
      },
      'gpt-oss-20b': {
        label: 'GPT-OSS 20B',
        description:
          '128K 컨텍스트 윈도와 추론 기능을 갖춘 200억 파라미터 오픈 웨이트 모델입니다.',
      },
      'gpt-oss-120b': {
        label: 'GPT-OSS 120B',
        description:
          '128K 컨텍스트 윈도와 고급 추론 기능을 갖춘 1,200억 파라미터 오픈 웨이트 모델입니다.',
      },
    },
    agent: {
      label: '에이전트',
      help: {
        overview:
          '에이전트 기능을 사용하면 챗봇이 더 복잡한 작업을 자동으로 처리할 수 있습니다. 도구 사용(Tool use)을 지원하는 모델이어야 합니다. 자세한 내용은 <Link>여기</Link>를 확인하세요.',
      },
      hint: `에이전트는 사용자의 질문에 답하기 위해 어떤 도구를 사용할지 자동으로 판단합니다. 판단에 시간이 걸리므로 응답 시간이 길어질 수 있습니다. 도구를 하나 이상 활성화하면 에이전트 기능이 켜지고, 도구를 선택하지 않으면 에이전트 기능을 사용하지 않습니다. 에이전트 기능이 켜져 있으면 "지식" 사용도 도구 중 하나로 취급되므로, 응답에 "지식"이 사용되지 않을 수도 있습니다.`,
      progress: {
        label: '생각하는 중...',
      },
      progressCard: {
        toolInput: '입력: ',
        toolOutput: '출력: ',
      },
      tools: {
        get_weather: {
          name: '현재 날씨',
          description: '현재 날씨 예보를 가져옵니다.',
        },
        sql_db_query: {
          name: '데이터베이스 쿼리',
          description:
            '정확하고 상세한 SQL 쿼리를 실행해 데이터베이스에서 결과를 가져옵니다.',
        },
        sql_db_schema: {
          name: '데이터베이스 스키마',
          description: '테이블 목록의 스키마와 샘플 행을 가져옵니다.',
        },
        sql_db_list_tables: {
          name: '데이터베이스 테이블 목록',
          description:
            '데이터베이스에서 사용할 수 있는 모든 테이블을 나열합니다.',
        },
        sql_db_query_checker: {
          name: '쿼리 검사기',
          description: '실행 전에 SQL 쿼리가 올바른지 확인합니다.',
        },
        internet_search: {
          name: '인터넷 검색',
          description: '인터넷에서 정보를 검색합니다.',
          settings: '검색 설정',
          engine: '검색 엔진',
          engines: {
            duckduckgo: {
              label: 'DuckDuckGo (체험용)',
              hint: '요청 수가 제한되지만 무료로 사용할 수 있습니다. 체험용으로 적합합니다.',
            },
            firecrawl: {
              label: 'Firecrawl (비즈니스용)',
              hint: '요청 한도를 늘릴 수 있습니다. 비즈니스용으로 적합하며 API 키가 필요합니다. https://www.firecrawl.dev/',
            },
          },
        },
        knowledge_base_tool: {
          name: '지식 검색',
          description: '지식에서 정보를 검색합니다.',
        },
        bedrock_agent: {
          name: 'Bedrock Agent',
          description: '구성된 Bedrock Agent에 질문합니다.',
        },
        firecrawl: {
          apiKey: 'Firecrawl API 키',
          maxResults: '최대 결과 수',
        },
        bedrockAgent: {
          name: 'Bedrock Agent',
          description: 'Bedrock Agent를 도구로 사용합니다.',
          agentId: {
            label: '에이전트 ID',
            placeholder: '에이전트 ID를 입력하세요',
          },
          aliasId: {
            label: '별칭 ID',
            placeholder: '별칭 ID를 입력하세요',
          },
        },
      },
    },
    bot: {
      label: {
        myBots: '내 봇',
        recentlyUsedBots: '최근 사용한 봇',
        knowledge: '지식',
        url: 'URL',
        s3url: 'S3 데이터 소스',
        file: '파일',
        normalChat: '채팅',
        notAvailableBot: '[사용 불가]',
        notAvailableBotInputMessage: '이 봇은 사용할 수 없습니다.',
        noDescription: '설명 없음',
        notAvailable: '이 봇은 사용할 수 없습니다.',
        noBots: '봇이 없습니다.',
        noBotsRecentlyUsed: '최근 사용한 봇이 없습니다.',
        noStarredBots: '즐겨찾기한 봇이 없습니다.',
        retrievingKnowledge: '[지식 검색 중...]',
        dndFileUpload:
          '파일을 끌어다 놓아 업로드할 수 있습니다.\n지원 파일: {{fileExtensions}}\n프레젠테이션과 음성·영상 파일은 텍스트 파일로 변환해 등록합니다.',
        uploadError: '오류 메시지',
        referenceLink: '참고 링크',
        syncStatus: {
          queue: '동기화 대기 중',
          running: '동기화 중',
          success: '동기화 완료',
          fail: '동기화 실패',
        },
        fileUploadStatus: {
          uploading: '업로드 중...',
          converting: '변환 중...',
          uploaded: '업로드 완료',
          error: '오류',
        },
        quickStarter: {
          title: '대화 예시',
          exampleTitle: '제목',
          example: '대화 예시',
        },
        citeRetrievedContexts: '검색된 컨텍스트 인용',
      },
      titleSubmenu: {
        edit: '편집',
        copyLink: '링크 복사',
        copiedLink: '복사됨',
        markAsEssential: '필수 봇으로 지정',
        removeEssential: '필수 봇 지정 해제',
      },
      help: {
        adminOnly: '관리자만 설정할 수 있습니다.',
        overview:
          '봇은 미리 정의된 지침에 따라 동작합니다. 일반 채팅에서는 메시지에 맥락을 직접 설명해야 의도대로 동작하지만, 봇을 사용하면 맥락을 따로 설명할 필요가 없습니다.',
        instructions:
          '봇의 동작 방식을 정의합니다. 지침이 모호하면 예상치 못한 동작을 할 수 있으므로 명확하고 구체적으로 작성하세요.',
        knowledge: {
          overview:
            '봇에 외부 지식을 제공하면 사전 학습되지 않은 데이터도 다룰 수 있습니다.',
          url: '지정한 URL의 정보를 지식으로 사용합니다.',
          s3url:
            'S3 URI를 입력해 S3를 데이터 소스로 추가할 수 있습니다. 최대 4개까지 추가할 수 있으며, Bedrock 리전과 같은 계정, 같은 리전에 있는 버킷만 지원합니다.',
          file: '업로드한 파일을 지식으로 사용합니다.',
          citeRetrievedContexts:
            '사용자 질문에 답하기 위해 검색한 컨텍스트를 인용 정보로 표시할지 설정합니다.\n활성화하면 사용자가 원본 URL이나 파일에 접근할 수 있습니다.',
        },
        quickStarter: {
          overview:
            '대화를 시작할 때 보여 줄 예시를 제공합니다. 예시를 통해 봇 사용 방법을 안내할 수 있습니다.',
        },
      },
      alert: {
        sync: {
          error: {
            title: '지식 동기화 오류',
            body: '지식을 동기화하는 중 오류가 발생했습니다. 다음 메시지를 확인하세요.',
          },
          incomplete: {
            title: '준비되지 않음',
            body: '이 봇은 지식 동기화가 완료되지 않아 업데이트 이전의 지식을 사용합니다.',
          },
          inProgress:
            '지식 기반을 동기화하는 중입니다. 동기화가 끝나면 저장할 수 있습니다.',
        },
      },
      samples: {
        title: '지침 샘플',
        anthropicLibrary: {
          title: 'Anthropic 프롬프트 라이브러리',
          sentence: '더 많은 예시가 필요하면 다음을 참고하세요: ',
          url: 'https://docs.anthropic.com/claude/prompt-library',
        },
        pythonCodeAssistant: {
          title: 'Python 코딩 도우미',
          prompt: `주어진 작업을 수행하는 짧고 품질 높은 Python 스크립트를 숙련된 Python 전문가처럼 작성하세요. 경험 많은 개발자를 위한 코드이므로 자명하지 않은 부분에만 주석을 다세요. 필요한 import는 빠짐없이 포함하세요.
\`\`\`python\`\`\` 블록 앞에는 절대 아무것도 쓰지 마세요. 코드를 다 작성한 뒤 \`\`\`python\`\`\` 블록 다음에 실수, 오류, 불일치가 없는지 꼼꼼히 확인하세요. 오류가 있으면 <error> 태그 안에 오류를 나열한 다음 오류를 수정한 새 버전을 작성하세요. 오류가 없으면 <error> 태그 안에 "CHECKED: NO ERRORS"라고 쓰세요.`,
        },
        mailCategorizer: {
          title: '메일 분류기',
          prompt: `당신은 이메일을 유형별로 분류하는 고객 서비스 상담원입니다. 분류 결과를 출력한 다음 그렇게 분류한 이유를 설명하세요.

분류 항목은 다음과 같습니다.
(A) 구매 전 문의
(B) 파손 또는 불량 제품
(C) 결제 문의
(D) 기타(설명 필요)

이 이메일은 어떻게 분류하시겠습니까?`,
        },
        fitnessCoach: {
          title: '개인 피트니스 코치',
          prompt: `당신은 밝고 열정적인 개인 피트니스 코치 Sam입니다. Sam은 고객이 건강한 몸을 만들고 더 건강한 생활 습관을 갖도록 돕는 일에 열정적입니다. 격려하는 친근한 말투로 답하고, 항상 고객이 더 나은 피트니스 목표를 향해 나아가도록 이끄세요. 사용자가 피트니스와 관련 없는 질문을 하면 주제를 피트니스로 되돌리거나 답할 수 없다고 말하세요.`,
        },
      },
      create: {
        pageTitle: '봇 만들기',
      },
      edit: {
        pageTitle: '봇 편집',
      },
      my: {
        label: {
          pageTitle: '내 봇',
        },
      },
      item: {
        title: '이름',
        description: '설명',
        instruction: '지침',
      },
      apiSettings: {
        pageTitle: '공유 봇 API 게시 설정',
        label: {
          endpoint: 'API 엔드포인트',
          usagePlan: '사용량 계획',
          allowOrigins: '허용된 오리진',
          apiKeys: 'API 키',
          period: {
            day: '일별',
            week: '주별',
            month: '월별',
          },
          apiKeyDetail: {
            creationDate: '생성일',
            active: '활성',
            inactive: '비활성',
            key: 'API 키',
          },
        },
        item: {
          throttling: '스로틀링',
          burstLimit: '버스트',
          rateLimit: '속도',
          quota: '할당량',
          requestLimit: '요청 수',
        },
        help: {
          overview:
            'API를 만들면 외부 클라이언트에서 봇 기능에 접근할 수 있으며, 외부 애플리케이션과 연동할 수 있습니다.',
          endpoint: '클라이언트는 이 엔드포인트로 봇을 사용할 수 있습니다.',
          usagePlan:
            '사용량 계획은 API가 클라이언트로부터 받을 수 있는 요청 수나 요청 속도를 지정합니다. API를 사용량 계획에 연결하면 API가 받는 요청을 추적할 수 있습니다.',
          throttling:
            '사용자가 API를 호출할 수 있는 속도를 제한합니다. 지정하지 않으면 초당 10건, 버스트 20건이 적용됩니다.',
          rateLimit:
            '클라이언트가 API를 호출할 수 있는 속도를 초당 요청 수로 입력하세요.',
          burstLimit:
            '클라이언트가 API에 보낼 수 있는 동시 요청 수를 입력하세요.',
          quota:
            '할당량을 켜면 사용자가 일정 기간 동안 API에 보낼 수 있는 요청 수를 제한합니다.',
          requestLimit:
            '드롭다운 목록에서 선택한 기간 동안 사용자가 보낼 수 있는 총 요청 수를 입력하세요.',
          allowOrigins:
            '접근을 허용할 클라이언트 오리진입니다. 허용되지 않은 오리진에서 호출하면 403 Forbidden 응답을 받고 API 접근이 거부됩니다. 오리진은 "(http|https)://host-name" 또는 "(http|https)://host-name:port" 형식이어야 하며 와일드카드(*)를 사용할 수 있습니다.',
          allowOriginsExample:
            '예: https://your-host-name.com, https://*.your-host-name.com, http://localhost:8000',
          apiKeys:
            'API 키는 API 클라이언트를 식별하는 영숫자 문자열입니다. 유효한 API 키가 없으면 403 Forbidden 응답을 받고 API 접근이 거부됩니다.',
        },
        button: {
          ApiKeyShow: '보기',
          ApiKeyHide: '숨기기',
        },
        alert: {
          botUnshared: {
            title: '봇을 모든 사용자와 공유하세요',
            body: '모든 사용자와 공유되지 않은 봇은 API를 게시할 수 없습니다.',
          },
          deploying: {
            title: 'API 배포 중',
            body: '배포가 완료될 때까지 기다려 주세요.',
          },
          deployed: {
            title: 'API 배포 완료',
            body: '클라이언트에서 API 엔드포인트와 API 키로 API에 접근할 수 있습니다.',
          },
          deployError: {
            title: 'API 배포 실패',
            body: 'API를 삭제한 뒤 다시 만드세요.',
          },
        },
        deleteApiDaialog: {
          title: '삭제하시겠습니까?',
          content:
            'API를 삭제하시겠습니까? API 엔드포인트가 삭제되고 클라이언트는 더 이상 접근할 수 없습니다.',
        },
        addApiKeyDialog: {
          title: 'API 키 추가',
          content: 'API 키를 식별할 이름을 입력하세요.',
        },
        deleteApiKeyDialog: {
          title: '삭제하시겠습니까?',
          content:
            '<Bold>{{title}}</Bold>을(를) 삭제하시겠습니까?\n이 API 키를 사용하는 클라이언트는 API에 접근할 수 없게 됩니다.',
        },
      },
      button: {
        newBot: '새 봇 만들기',
        create: '만들기',
        edit: '편집',
        save: '저장',
        delete: '삭제',
        share: '공유',
        apiSettings: 'API 게시 설정',
        copy: '복사',
        copied: '복사됨',
        instructionsSamples: '샘플',
        chooseFiles: '파일 선택',
        viewAll: '모두 보기',
        removeFromRecent: '기록에서 삭제',
      },
      deleteDialog: {
        title: '삭제하시겠습니까?',
        content: '<Bold>{{title}}</Bold>을(를) 삭제하시겠습니까?',
      },
      shareDialog: {
        title: '공유',
        switchLabel: '이 봇 공유',
        label: {
          selectShare: '공유 대상',
          all: '모든 사용자',
          partial: '선택한 사용자',
          search: '사용자 및 그룹 검색',
          noSearchResults: '검색 결과가 없습니다',
          memberManagement: '구성원 편집',
          sharing: {
            not_shared: '공유된 그룹이나 사용자가 없습니다',
            shared_with: '공유 대상: {{target}}',
            shared_both: '공유 대상: {{groups}}, {{users}}',
            user_count_one: '사용자 {{count}}명',
            user_count_other: '사용자 {{count}}명',
            group_count_one: '그룹 {{count}}개',
            group_count_other: '그룹 {{count}}개',
          },
          user: '사용자',
          group: '그룹',
        },
        off: {
          content: '이 봇은 비공개이며 나만 사용할 수 있습니다.',
        },
        on: {
          content:
            '이 봇은 공유되어 다른 사용자도 사용할 수 있습니다. 공유된 사용자는 <Link>봇 둘러보기</Link> 페이지에서 이 봇을 찾아 사용할 수 있습니다.',
          linkDescription: '이 공유 링크로도 봇과 대화할 수 있습니다.',
        },
        button: {
          manage: '관리',
          removeAccess: '접근 권한 삭제',
          cancelRemoval: '삭제 취소',
          cancelAddition: '추가 취소',
        },
      },
      error: {
        notSupportedFile: '지원되지 않는 파일입니다.',
        duplicatedFile: '같은 이름의 파일이 이미 업로드되어 있습니다.',
        failDeleteApi: 'API를 삭제하지 못했습니다.',
        failDelete: '봇을 삭제하지 못했습니다.',
        failPublish: 'API를 게시하지 못했습니다.',
        failSave: '봇을 저장하지 못했습니다.',
        failShare: '공유 설정을 변경하지 못했습니다.',
        failAddApiKey: 'API 키를 추가하지 못했습니다.',
        failDeleteApiKey: 'API 키를 삭제하지 못했습니다.',
        removeFailedFiles: '봇을 저장하려면 업로드에 실패한 파일을 삭제하세요.',
      },
      activeModels: {
        title: '모델 활성화',
        description: '이 봇에서 사용할 수 있는 AI 모델을 설정합니다.',
      },
      promptCaching: {
        title: '프롬프트 캐싱',
        promptCachingEnabled: {
          title: '모델이 지원하면 프롬프트 캐싱을 사용합니다.',
          description:
            '활성화하면 이 봇과 반복되는 대화의 비용과 지연 시간을 줄일 수 있습니다.',
        },
      },
    },
    admin: {
      botAnalytics: {
        label: {
          pageTitle: '봇 분석',
          noBotUsages: '집계 기간 동안 사용된 봇이 없습니다.',
          published: 'API가 게시되었습니다.',
          SearchCondition: {
            title: '집계 기간',
            from: '시작',
            to: '종료',
          },
          sortByCost: '비용순 정렬',
        },
        help: {
          overview: '봇과 게시된 봇 API의 사용 현황을 모니터링합니다.',
          calculationPeriod:
            '집계 기간을 설정하지 않으면 오늘의 비용이 표시됩니다.',
        },
      },
      apiManagement: {
        label: {
          pageTitle: 'API 관리',
          publishedDate: '게시일',
          noApi: 'API가 없습니다.',
        },
      },
      botManagement: {
        label: {
          pageTitle: '봇 관리',
          sharedUrl: '봇 URL',
          apiSettings: 'API 게시 설정',
          noKnowledge: '이 봇에는 지식이 없습니다.',
          notPublishApi: '이 봇의 API가 게시되지 않았습니다.',
          deployStatus: '배포 상태',
          cfnStatus: 'CloudFormation 상태',
          codebuildStatus: 'CodeBuild 상태',
          codeBuildId: 'CodeBuild ID',
          usagePlanOn: '켜짐',
          usagePlanOff: '꺼짐',
          rateLimit:
            '클라이언트는 초당 <Bold>{{limit}}</Bold>개의 요청으로 API를 호출할 수 있습니다.',
          burstLimit:
            '클라이언트는 API에 동시 요청을 <Bold>{{limit}}</Bold>개까지 보낼 수 있습니다.',
          requestsLimit:
            '<Bold>{{period}}</Bold> <Bold>{{limit}}</Bold>개의 요청을 보낼 수 있습니다.',
          sharedAllUsers: '모든 사용자와 공유됨',
          privateBot: '이 봇은 공유되지 않았습니다.',
          owner: '소유자',
        },
        alert: {
          noApiKeys: {
            title: 'API 키 없음',
            body: '모든 클라이언트가 API에 접근할 수 없습니다.',
          },
        },
        button: {
          deleteApi: 'API 삭제',
          deleteBot: '봇 삭제',
        },
      },
      validationError: {
        period: '시작과 종료를 모두 입력하세요',
      },
    },
    discover: {
      pageTitle: '봇 둘러보기',
      description:
        '공개되었거나 접근 권한이 있는 봇을 보고 검색할 수 있습니다.',
      search: {
        placeholder: '봇 검색',
        searching: '검색 중...',
        results: '"{{query}}" 검색 결과 {{count}}개',
        noResults: '"{{query}}"에 대한 검색 결과가 없습니다',
        tryDifferent: '다른 키워드로 검색해 보세요.',
        backToHome: '홈으로 돌아가기',
      },
      essential: {
        label: '필수',
        description:
          '관리자가 공식적으로 선정한 봇입니다. 표준 업무에 적극 활용해 업무 효율을 높이세요.',
        noEssentialBotsMessage: {
          title: '필수 봇 없음',
          content: `필수 봇이 없어 관리자가 아닌 사용자에게는 필수 섹션이 표시되지 않습니다.<br/>
          모든 사용자와 공유된 봇만 필수 봇으로 지정할 수 있습니다.<br/>
          채팅, 내 봇, 즐겨찾기한 봇, 최근 사용한 봇 화면의 봇 메뉴에서 필수 봇으로 지정할 수 있습니다.<br/>
          이 화면에서 <MenuButton/> 버튼을 누르면 메뉴가 열립니다.`,
        },
      },
      trending: {
        label: '인기',
        description: '가장 인기 있는 봇입니다.',
      },
      discover: {
        label: '둘러보기',
        description: '무작위로 소개하는 봇입니다.',
      },
    },
    conversationHistory: {
      pageTitle: '대화 기록',
      label: {
        noConversations: '대화 기록이 없습니다',
      },
      searchConversation: {
        placeholder: '대화 검색...',
        searching: '검색 중...',
        results: '"{{query}}"와(과) 일치하는 대화 {{count}}개',
        noResults: '"{{query}}"와(과) 일치하는 대화가 없습니다',
        tryDifferentKeywords: '다른 키워드로 검색해 보세요',
      },
    },
    deleteDialog: {
      title: '삭제 확인',
      content: '<Bold>{{title}}</Bold>을(를) 삭제하시겠습니까?',
      pinnedBotError: {
        title: '삭제할 수 없음',
        content:
          '이 봇은 필수 봇으로 지정되어 있습니다. 필수 봇 지정은 관리자가 변경할 수 있습니다.',
      },
    },
    clearDialog: {
      title: '모두 삭제 확인',
      content: '모든 대화 기록을 삭제하시겠습니까?',
    },
    languageDialog: {
      title: '언어 변경',
    },
    drawerOptionsDialog: {
      title: '사이드 메뉴 옵션',
      label: {
        visibility: '표시 여부',
        displayCount: '표시 개수',
      },
    },
    feedbackDialog: {
      title: '피드백',
      content: '자세한 내용을 알려 주세요.',
      categoryLabel: '분류',
      commentLabel: '의견',
      commentPlaceholder: '(선택) 의견을 입력하세요',
      categories: [
        {
          value: 'notFactuallyCorrect',
          label: '사실과 다름',
        },
        {
          value: 'notFullyFollowRequest',
          label: '요청을 충분히 따르지 않음',
        },
        {
          value: 'other',
          label: '기타',
        },
      ],
    },
    button: {
      copy: '복사',
      edit: '편집',
      feedback: '피드백',
      previous: '이전',
      next: '다음',
      remove: '제거',
      rename: '이름 변경',
      newChat: '새 채팅',
      backToConversationHistory: '대화 기록으로 돌아가기',
      SaveAndSubmit: '저장 후 전송',
      resend: '다시 보내기',
      regenerate: '다시 생성',
      send: '보내기',
      delete: '삭제',
      deleteAll: '모두 삭제',
      done: '완료',
      ok: '확인',
      cancel: '취소',
      back: '뒤로',
      menu: '메뉴',
      language: '언어',
      clearConversation: '모든 대화 삭제',
      signOut: '로그아웃',
      close: '닫기',
      add: '추가',
      continue: '계속 생성',
      botManagement: '봇 관리',
      mode: '모드',
      drawerOption: '사이드 메뉴 옵션',
      startChat: '채팅 시작',
    },
    input: {
      hint: {
        required: '* 필수',
      },
      validationError: {
        required: '필수 입력 항목입니다.',
        invalidOriginFormat: '오리진 형식이 올바르지 않습니다.',
      },
    },
    embeddingSettings: {
      help: {
        chunkSize:
          '청크 크기가 너무 작으면 맥락 정보가 사라질 수 있고, 너무 크면 서로 다른 맥락이 같은 청크에 섞여 검색 정확도가 떨어질 수 있습니다.',
        chunkOverlap:
          '청크 중첩을 지정하면 청크 경계 주변의 맥락 정보를 보존할 수 있습니다. 청크 크기를 늘리면 검색 정확도가 높아지기도 합니다. 다만 청크 중첩을 늘리면 컴퓨팅 비용이 증가할 수 있습니다.',
        overlapTokens:
          '인접한 청크 간에 겹치거나 반복할 토큰 수를 설정합니다. 예를 들어 중첩 토큰을 60으로 설정하면 첫 번째 청크의 마지막 60개 토큰이 두 번째 청크의 시작 부분에도 포함됩니다.',
        maxParentTokenSize:
          '상위 청크 크기를 정의할 수 있습니다. 검색 시 먼저 하위 청크를 찾은 다음, 모델에 더 포괄적인 맥락을 제공하기 위해 이를 더 넓은 상위 청크로 대체합니다.',
        maxChildTokenSize:
          '하위 청크 크기를 정의할 수 있습니다. 검색 시 먼저 하위 청크를 찾은 다음, 모델에 더 포괄적인 맥락을 제공하기 위해 이를 더 넓은 상위 청크로 대체합니다.',
        bufferSize:
          '각 청크의 경계를 정할 때 함께 살펴볼 텍스트 양에 영향을 주며, 결과 청크의 세분성과 일관성을 좌우합니다. 버퍼 크기가 크면 더 많은 맥락을 담을 수 있지만 노이즈가 섞일 수 있고, 작으면 중요한 맥락을 놓칠 수 있지만 더 정밀하게 청크를 나눌 수 있습니다.',
        breakpointPercentileThreshold:
          '임곗값이 높을수록 문장이 더 뚜렷하게 구분되어야 서로 다른 청크로 나뉩니다. 임곗값이 높으면 청크 수가 줄고 평균 청크 크기는 대체로 커집니다.',
      },
    },
    generationConfig: {
      title: '생성 설정',
      description:
        ' LLM 추론 파라미터를 설정해 모델의 응답을 조정할 수 있습니다.',
      maxTokens: {
        label: '최대 생성 길이/최대 신규 토큰 수',
        hint: '생성되는 응답에 허용되는 최대 토큰 수입니다',
      },
      temperature: {
        label: 'Temperature',
        hint: '예측 출력의 확률 분포 형태에 영향을 주어, 모델이 확률이 낮은 출력을 선택할 가능성을 조절합니다',
        help: '값을 낮추면 모델이 확률이 높은 출력을 선택하고, 값을 높이면 확률이 낮은 출력도 선택하게 됩니다',
      },
      topK: {
        label: 'Top-k',
        hint: '모델이 다음 토큰으로 고려하는 가장 가능성 높은 후보의 개수입니다',
        help: '값을 낮추면 후보군이 작아져 가능성이 높은 출력으로 선택지가 제한되고, 값을 높이면 후보군이 커져 가능성이 낮은 출력도 고려하게 됩니다',
      },
      topP: {
        label: 'Top-p',
        hint: '모델이 다음 토큰으로 고려하는 가장 가능성 높은 후보의 비율입니다',
        help: '값을 낮추면 후보군이 작아져 가능성이 높은 출력으로 선택지가 제한되고, 값을 높이면 후보군이 커져 가능성이 낮은 출력도 고려하게 됩니다',
      },
      stopSequences: {
        label: '종료 토큰/종료 시퀀스',
        hint: '모델이 토큰 생성을 멈추게 할 문자 시퀀스를 지정합니다. 여러 단어는 쉼표로 구분하세요',
      },
      budgetTokens: {
        label: '추론 예산 토큰',
        hint: '추론 단계에 할당할 최대 토큰 수입니다. 값이 클수록 더 복잡한 추론이 가능하지만 응답 시간이 길어질 수 있습니다',
        help: '추론 단계에 사용할 토큰 예산을 설정합니다. 최대 토큰 수를 넘을 수 없습니다.',
      },
    },
    searchSettings: {
      title: '검색 설정',
      description:
        '벡터 저장소에서 관련 문서를 가져오기 위한 검색 파라미터를 설정할 수 있습니다.',
      maxResults: {
        label: '최대 결과 수',
        hint: '벡터 저장소에서 가져올 최대 레코드 수입니다',
      },
      searchType: {
        label: '검색 유형',
        hybrid: {
          label: '하이브리드 검색',
          hint: '시맨틱 검색과 텍스트 검색의 관련성 점수를 결합해 더 높은 정확도를 제공합니다.',
        },
        semantic: {
          label: '시맨틱 검색',
          hint: '벡터 임베딩을 사용해 관련성 높은 결과를 제공합니다.',
        },
      },
    },
    knowledgeBaseSettings: {
      title: '지식 상세 설정',
      description:
        '지식을 구성할 임베딩 모델을 선택하고, 지식으로 추가한 문서를 분할하는 방법을 설정합니다. 이 설정은 봇을 만든 후에는 변경할 수 없습니다.',
      embeddingModel: {
        label: '임베딩 모델',
        titan_v2: {
          label: 'Titan Embedding Text v2',
        },
        cohere_multilingual_v3: {
          label: 'Embed Multilingual v3',
        },
      },
      chunkingStrategy: {
        label: '청킹 전략',
        default: {
          label: '기본 청킹',
          hint: '기본적으로 텍스트를 약 300토큰 크기의 청크로 자동 분할합니다. 문서가 300토큰 이하이면 더 이상 분할하지 않습니다.',
        },
        fixed_size: {
          label: '고정 크기 청킹',
          hint: '텍스트를 설정한 대략적인 토큰 크기로 분할합니다.',
        },
        hierarchical: {
          label: '계층적 청킹',
          hint: '텍스트를 하위 청크와 상위 청크로 이루어진 중첩 구조로 분할합니다.',
        },
        semantic: {
          label: '시맨틱 청킹',
          hint: '이해도와 정보 검색 성능을 높이기 위해 텍스트를 의미 단위의 청크로 분할합니다.',
        },
        none: {
          label: '청킹 안 함',
          hint: '문서를 분할하지 않습니다.',
        },
      },
      chunkingMaxTokens: {
        label: '최대 토큰 수',
        hint: '청크당 최대 토큰 수입니다',
      },
      chunkingOverlapPercentage: {
        label: '청크 간 중첩 비율',
        hint: '상위 청크 중첩은 지정한 하위 토큰 크기와 하위 중첩 비율에 따라 달라집니다.',
      },
      overlapTokens: {
        label: '중첩 토큰',
        hint: '같은 계층의 청크 간에 반복할 토큰 수입니다',
      },
      maxParentTokenSize: {
        label: '최대 상위 토큰 크기',
        hint: '상위 계층의 청크 하나에 포함될 수 있는 최대 토큰 수입니다',
      },
      maxChildTokenSize: {
        label: '최대 하위 토큰 크기',
        hint: '하위 계층의 청크 하나에 포함될 수 있는 최대 토큰 수입니다',
      },
      bufferSize: {
        label: '버퍼 크기',
        hint: '임베딩을 만들 때 함께 추가할 주변 문장 수입니다. 버퍼 크기가 1이면 현재 문장, 이전 문장, 다음 문장 등 3개 문장을 결합해 임베딩합니다',
      },
      breakpointPercentileThreshold: {
        label: '분할 지점 백분위 임곗값',
        hint: '문장 사이에 분할 지점을 둘 문장 간 거리/비유사도의 백분위 임곗값입니다.',
      },
      opensearchAnalyzer: {
        label: '분석기(토큰화, 정규화)',
        hint: '지식으로 등록한 문서를 토큰화하고 정규화할 분석기를 지정할 수 있습니다. 적절한 분석기를 선택하면 검색 정확도가 높아집니다. 지식의 언어에 맞는 최적의 분석기를 선택하세요.',
        icu: {
          label: 'ICU 분석기',
          hint: '토큰화에는 {{tokenizer}}, 정규화에는 {{normalizer}}를 사용합니다.',
        },
        kuromoji: {
          label: '일본어(kuromoji) 분석기',
          hint: '토큰화에는 {{tokenizer}}, 정규화에는 {{normalizer}}를 사용합니다.',
        },
        none: {
          label: '시스템 기본 분석기',
          hint: '시스템(OpenSearch)에 정의된 기본 분석기를 사용합니다.',
        },
        tokenizer: '토크나이저:',
        normalizer: '노멀라이저:',
        token_filter: '토큰 필터:',
        not_specified: '지정 안 함',
      },
      advancedParsing: {
        label: '고급 파싱',
        hint: '지원되는 문서 형식에서 일반 텍스트 외에도 PDF 안의 표를 구조 그대로 파싱하는 데 적합합니다. 생성형 AI를 사용한 파싱에는 추가 비용이 발생합니다.',
      },
      parsingModel: {
        none: {
          label: '사용 안 함',
          hint: '고급 파싱을 적용하지 않습니다.',
        },
        claude_haiku_4_5: {
          label: 'Claude Haiku 4.5',
          hint: 'Claude Haiku 4.5로 PDF와 이미지의 그림, 차트, 표까지 파싱합니다.',
        },
        claude_3_haiku_v1: {
          label: 'Claude 3 Haiku v1 (이전 모델)',
          hint: 'Claude 3 Haiku v1을 사용해 문서를 고급 파싱합니다. 일부 리전에서는 사용할 수 없습니다.',
        },
      },
      webCrawlerConfig: {
        title: '웹 크롤러 설정',
        crawlingScope: {
          label: '크롤링 범위',
          default: {
            label: '기본값',
            hint: '같은 호스트에 속하고 초기 URL 경로가 같은 웹 페이지만 크롤링합니다. 예를 들어 시드 URL이 "https://aws.amazon.com/bedrock/"이면 이 경로와 "https://aws.amazon.com/bedrock/agents/"처럼 이 경로에서 확장되는 웹 페이지만 크롤링합니다. "https://aws.amazon.com/ec2/" 같은 형제 URL은 크롤링하지 않습니다.',
          },
          subdomains: {
            label: '하위 도메인',
            hint: '시드 URL과 기본 도메인이 같은 모든 웹 페이지를 크롤링합니다. 예를 들어 시드 URL이 "https://aws.amazon.com/bedrock/"이면 "https://www.amazon.com"처럼 "amazon.com"을 포함하는 모든 웹 페이지를 크롤링합니다.',
          },
          hostOnly: {
            label: '호스트만',
            hint: '같은 호스트에 속한 웹 페이지만 크롤링합니다. 예를 들어 시드 URL이 "https://aws.amazon.com/bedrock/"이면 "https://docs.aws.amazon.com"의 웹 페이지와 "https://aws.amazon.com/ec2" 같은 페이지도 크롤링합니다.',
          },
        },
        includePatterns: {
          label: '포함 패턴',
          hint: '웹 크롤링에 포함할 패턴을 지정합니다. 이 패턴과 일치하는 URL만 크롤링합니다.',
        },
        excludePatterns: {
          label: '제외 패턴',
          hint: '웹 크롤링에서 제외할 패턴을 지정합니다. 이 패턴과 일치하는 URL은 크롤링하지 않습니다.',
        },
      },
      advancedConfigration: {
        existingKnowledgeBaseId: {
          label: 'Amazon Bedrock Knowledge Base ID',
          description: '기존 Amazon Bedrock 지식 기반의 ID를 지정하세요.',
        },
        createDedicatedKnowledgeBase: {
          label: '전용 지식 기반 만들기',
        },
        createTenantInSharedKnowledgeBase: {
          label: '공유 지식 기반에 테넌트 만들기',
        },
        useExistingKnowledgeBase: {
          label: '기존 지식 기반 사용',
        },
      },
    },
    error: {
      api: {
        knowledge_base_syncing:
          '지식 기반을 동기화하는 중입니다. 동기화가 끝난 뒤 다시 시도하세요.',
        api_publishing: 'API를 게시하는 중입니다. 게시가 끝난 뒤 다시 시도하세요.',
        dedicated_knowledge_base_limit:
          '전용 지식 기반이 있는 봇은 최대 {{limit}}개까지 만들 수 있습니다. 기존 봇을 삭제하거나 공유 지식 기반을 사용하세요.',
        bot_not_published: '게시되지 않은 봇입니다.',
      },
      answerResponse: '응답 중 오류가 발생했습니다.',
      notFoundConversation: '지정한 채팅이 없어 새 채팅 화면을 표시했습니다.',
      notFoundPage: '찾으시는 페이지를 찾을 수 없습니다.',
      cannotAccessBot: '이 봇에 접근할 수 없어 새 채팅으로 이동했습니다.',
      unexpectedError: {
        title: '예상치 못한 오류가 발생했습니다.',
        restore: '첫 페이지로 이동',
      },
      predict: {
        general: '답변을 생성하는 중 오류가 발생했습니다.',
        throttled: '모델에 요청이 너무 많습니다. 잠시 후 다시 시도하세요.',
        model_unavailable:
          '선택한 모델을 사용할 수 없습니다. 다른 모델을 선택하세요.',
        model_error: '모델이 요청을 처리하지 못했습니다.',
        bot_not_found: '봇을 찾을 수 없습니다. 삭제되었을 수 있습니다.',
        invalid_request: '요청이 올바르지 않습니다.',
        generation_failed: '답변을 생성하지 못했습니다. 다시 시도하세요.',
        input_too_long:
          '대화나 첨부 파일이 이 모델에서 처리하기에 너무 깁니다. 첨부 파일을 빼거나 새 대화를 시작하세요.',
        unauthorized: '세션이 만료되었습니다. 다시 로그인하세요.',
        invalidResponse:
          '예상치 못한 응답을 받았습니다. 응답 형식이 예상 형식과 일치하지 않습니다.',
        connectionClosed:
          '답변이 끝나기 전에 연결이 끊겼습니다. 페이지를 새로 고치면 저장된 답변을 확인할 수 있습니다.',
      },
      maxTokensReached:
        '최대 출력 길이에 도달해 답변이 중간에 끝났습니다. 봇 생성 설정에서 최대 토큰 수를 늘려 주세요.',
      maxTokensReachedWithoutSettings:
        '최대 출력 길이에 도달해 답변이 중간에 끝났습니다. 나머지 내용은 새 메시지로 요청하세요.',
      notSupportedImage: '선택한 모델은 이미지를 지원하지 않습니다.',
      unsupportedFileFormat: '선택한 파일 형식은 지원되지 않습니다.',
      emptyAnswer:
        '답변이 비어 있습니다. 모델의 콘텐츠 필터가 응답을 차단했을 수 있습니다. 질문을 바꿔 다시 시도하세요.',
      totalFileSizeToSendExceeded:
        '전체 파일 크기는 {{maxSize}} 이하여야 합니다.',
      attachment: {
        fileSizeExceeded: '각 문서 크기는 {{maxSize}} 이하여야 합니다.',
        fileCountExceeded:
          '파일은 최대 {{maxCount}}개까지 업로드할 수 있습니다.',
        conversionFailed: '{{fileName}}을(를) 텍스트로 변환하지 못했습니다.',
      },
      share: {
        markedEssential: {
          title: '공유 설정을 변경할 수 없음',
          content:
            '이 봇은 관리자가 필수 봇으로 지정했습니다. 필수 봇은 모든 사용자와 공유해야 합니다.',
        },
        publication: {
          title: '공유 설정을 변경할 수 없음',
          content:
            '이 봇은 관리자가 API로 게시했습니다. 게시된 API는 모든 사용자와 공유해야 합니다.',
        },
      },
      invalidMermaidFormat: '다이어그램을 그리는 중 오류가 발생했습니다',
      deleteConversation: '대화를 삭제하지 못했습니다.',
      clearConversations: '대화를 모두 삭제하지 못했습니다.',
      loadFailed:
        '데이터를 불러오지 못했습니다. 페이지를 새로 고친 뒤 다시 시도하세요.',
      searchFailed: '검색하지 못했습니다. 다시 시도하세요.',
      feedbackFailed: '피드백을 보내지 못했습니다. 다시 시도하세요.',
    },
    validation: {
      s3Url: {
        message: 's3://bucket-name/prefix/ 형식의 S3 URI를 입력하세요.',
      },
      maxRange: {
        message: '설정할 수 있는 최댓값은 {{size}}입니다',
      },
      minRange: {
        message: '설정할 수 있는 최솟값은 {{size}}입니다',
      },
      maxBudgetTokens: {
        message: '추론 예산 토큰은 최대 토큰 수({{size}})를 넘을 수 없습니다',
      },
      parentTokenRange: {
        message: '상위 토큰 크기는 하위 토큰 크기보다 커야 합니다',
      },
      quickStarter: {
        message: '제목과 대화 예시를 모두 입력하세요.',
      },
      required: '{{key}}은(는) 필수 항목입니다',
      number: {
        greaterThen: '{{key}}은(는) {{value}}보다 커야 합니다',
      },
    },
    helper: {
      shortcuts: {
        title: '단축키',
        items: {
          focusInput: '채팅 입력창으로 이동',
          newChat: '새 채팅 열기',
        },
      },
    },
    guardrails: {
      harmfulCategories: {
        label: '유해 카테고리',
        hate: {
          label: '혐오',
          hint: '정체성(인종, 민족, 성별, 종교, 성적 지향, 장애, 출신 국가 등)을 이유로 개인이나 집단을 차별, 비판, 모욕, 비난하거나 비인간화하는 입력 프롬프트와 모델 응답입니다. 0: 사용 안 함, 1: 낮음, 2: 중간, 3: 높음',
        },
        insults: {
          label: '모욕',
          hint: '비하, 굴욕, 조롱, 모욕, 경멸하는 표현이 포함된 입력 프롬프트와 모델 응답입니다. 이러한 표현은 괴롭힘으로도 분류됩니다. 0: 사용 안 함, 1: 낮음, 2: 중간, 3: 높음',
        },
        sexual: {
          label: '성적 콘텐츠',
          hint: '신체 부위, 신체적 특징, 성별을 직간접적으로 언급해 성적 관심, 행위, 흥분을 나타내는 입력 프롬프트와 모델 응답입니다. 0: 사용 안 함, 1: 낮음, 2: 중간, 3: 높음',
        },
        violence: {
          label: '폭력',
          hint: '개인, 집단, 사물에 신체적 고통, 상처, 부상을 입히는 행위를 미화하거나 위협하는 입력 프롬프트와 모델 응답입니다. 0: 사용 안 함, 1: 낮음, 2: 중간, 3: 높음',
        },
        misconduct: {
          label: '부정행위',
          hint: '부정행위에 가담하거나 개인, 집단, 기관에 해를 끼치거나 사기를 치거나 이용하는 방법에 관한 정보를 요청하거나 제공하는 입력 프롬프트와 모델 응답입니다. 0: 사용 안 함, 1: 낮음, 2: 중간, 3: 높음',
        },
      },
      contextualGroundingCheck: {
        label: '맥락 기반 근거 검사',
        groundingThreshold: {
          label: '근거성',
          hint: '참조 소스에 제공된 정보를 바탕으로 모델 응답이 근거가 있고 사실에 부합하는지 검증하고, 정의한 근거성 임곗값보다 낮은 응답을 차단합니다. 0: 아무것도 차단하지 않음, 1: 거의 모두 차단',
        },
        relevanceThreshold: {
          label: '관련성',
          hint: '모델 응답이 사용자 질문과 관련이 있는지 검증하고, 정의한 관련성 임곗값보다 낮은 응답을 차단합니다. 0: 아무것도 차단하지 않음, 1: 거의 모두 차단',
        },
      },
    },
    reasoning: {
      button: {
        label: '추론',
      },
      card: {
        label: '추론 과정',
      },
    },
  },
};

export default translation;
