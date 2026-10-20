import { DESCRIPTION_MAX, TITLE_MAX } from './types'

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
