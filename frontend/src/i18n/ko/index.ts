// Check for any missing settings by uncomment
// import en from '../en';
// const translation: typeof en = {
const translation = {
  translation: {
    app: {
      name: 'Bedrock Chat',
      inputMessage: '입력해 주십시오',
      pinnedBots: '고정된 봇',
    },
    deleteDialog: {
      title: '삭제 확인',
      content: '채팅 "<Bold>{{title}}</Bold>"을(를) 삭제하시겠습니까?',
    },
    clearDialog: {
      title: '삭제 확인',
      content: '모든 대화 기록을 삭제하시겠습니까?',
    },
    languageDialog: {
      title: '언어 변경',
    },
    button: {
      copy: '복사',
      edit: '편집',
      feedback: '피드백',
      previous: '이전',
      next: '다음',
      remove: '제거',
      rename: '이름 변경',
      newChat: '새로운 채팅',
      SaveAndSubmit: '변경 & 전송',
      resend: '재전송',
      regenerate: '재생성',
      delete: '삭제',
      deleteAll: '모두 삭제',
      ok: '확인',
      cancel: '취소',
      menu: '메뉴',
      language: '언어 변경',
      clearConversation: '모든 대화 지우기',
      signOut: '로그아웃',
    },
    error: {
      answerResponse: '응답 중 오류가 발생했습니다.',
      notFoundConversation:
        '지정된 채팅이 존재하지 않기 때문에 새로운 채팅 화면을 표시했습니다.',
      notFoundPage: '찾고 있는 페이지를 찾을 수 없습니다.',
      predict: {
        general: '예측 중 오류가 발생했습니다.',
        invalidResponse: '예상치 못한 응답이 반환되었습니다.',
        connectionClosed:
          '답변이 끝나기 전에 연결이 끊겼습니다. 페이지를 새로 고치면 저장된 답변을 확인할 수 있습니다.',
      },
      maxTokensReached:
        '최대 출력 길이에 도달해 답변이 중간에 끝났습니다. 봇 생성 설정에서 최대 토큰 수를 늘려 주세요.',
    },
  },
};

export default translation;
