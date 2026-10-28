import { ApiError } from './api'

// 목록을 불러오지 못한 원인을 사용자가 알 수 있는 문구로 바꾼다 (R-009).
export function loadErrorMessage(e: unknown): string {
  // 네트워크 오류, 또는 프록시가 백엔드에 닿지 못한 경우(502/503/504)
  const unreachable =
    e instanceof TypeError ||
    (e instanceof ApiError && [502, 503, 504].includes(e.status))
  if (unreachable) {
    return 'API에 연결할 수 없습니다. 백엔드가 실행 중인지 확인한 뒤 다시 시도하세요.'
  }
  if (e instanceof ApiError && e.status === 500) {
    return '저장소 파일을 읽을 수 없습니다. 카드를 표시하지 않습니다.'
  }
  return '카드를 불러오지 못했습니다. 잠시 뒤 다시 시도하세요.'
}

// 할 일 초안 만들기(R-016)가 실패한 원인을 문구로 바꾼다. 서버 응답 내용은 담지 않는다.
export function draftErrorMessage(e: unknown): string {
  if (e instanceof ApiError && e.status === 503) {
    return '지금은 AI 기능을 쓸 수 없습니다. 직접 입력해 주세요.'
  }
  return '할 일을 만들지 못했습니다. 다시 눌러 보세요.'
}

export const REGISTER_FAILED_NONE = '등록하지 못했습니다. 카드는 만들어지지 않았습니다.'

export function registerPartialMessage(total: number, done: number): string {
  return `${total}개 중 ${done}개를 등록했습니다. 남은 ${total - done}개는 모두 등록을 다시 눌러 주세요.`
}

// 가입·로그인이 실패한 원인을 사용자가 알 수 있는 문구로 바꾼다 (R-010).
export function authErrorMessage(e: unknown, mode: 'login' | 'signup'): string {
  if (e instanceof TypeError || (e instanceof ApiError && [502, 503, 504].includes(e.status))) {
    return 'API에 연결할 수 없습니다. 백엔드가 실행 중인지 확인한 뒤 다시 시도하세요.'
  }
  if (e instanceof ApiError) {
    // 아이디가 틀렸는지 비밀번호가 틀렸는지는 알려 주지 않는다.
    if (mode === 'login' && e.status === 401) return '아이디 또는 비밀번호가 올바르지 않습니다.'
    if (mode === 'signup' && e.status === 409) return '이미 있는 아이디입니다.'
    if (mode === 'signup' && e.status === 422) {
      return '아이디 또는 비밀번호가 규칙에 맞지 않습니다.'
    }
  }
  return mode === 'login'
    ? '로그인하지 못했습니다. 잠시 뒤 다시 시도하세요.'
    : '가입하지 못했습니다. 잠시 뒤 다시 시도하세요.'
}
