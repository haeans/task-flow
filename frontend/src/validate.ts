import {
  DESCRIPTION_MAX,
  PASSWORD_MAX,
  PASSWORD_MIN,
  TITLE_MAX,
  USERNAME_PATTERN,
} from './types'

// API와 같은 기준 (D-003, D-013, Q-007). 최종 판단은 API가 한다.
export function validateTaskInput(title: string, description: string): string | null {
  const t = title.trim()
  if (!t) return '제목을 입력하세요.'
  if (t.length > TITLE_MAX) return `제목은 ${TITLE_MAX}자 이하여야 합니다.`
  if (description.length > DESCRIPTION_MAX) {
    return `설명은 ${DESCRIPTION_MAX}자 이하여야 합니다.`
  }
  return null
}

// 가입 입력 검사. API와 같은 기준이며 최종 판단은 API가 한다 (Q-014).
export function validateSignupInput(username: string, password: string): string | null {
  if (!USERNAME_PATTERN.test(username)) return '아이디는 4~20자의 영문과 숫자만 쓸 수 있습니다.'
  if (password.length < PASSWORD_MIN || password.length > PASSWORD_MAX) {
    return `비밀번호는 ${PASSWORD_MIN}~${PASSWORD_MAX}자여야 합니다.`
  }
  return null
}

// 로그인 입력 검사. 규칙 검사는 하지 않고 비어 있는지만 본다. 틀린 값은 API가 401로 알린다.
export function validateLoginInput(username: string, password: string): string | null {
  if (!username || !password) return '아이디와 비밀번호를 입력하세요.'
  return null
}
