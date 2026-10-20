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
