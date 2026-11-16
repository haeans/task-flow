// 화면 상태 표시: 불러오는 중, 카드 없음, 실패 (R-009). 로그인하지 않음(B-5)은 로그인 화면으로 보낸다.

export const SESSION_ENDED_NOTICE = '로그인이 끝났습니다. 다시 로그인하세요.'

export function LoadingScreen() {
  return (
    <div className="screen" role="status" aria-live="polite">
      <p className="screen-title">불러오는 중...</p>
      <p>저장된 카드를 가져오고 있습니다.</p>
    </div>
  )
}

export function EmptyScreen({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="screen" role="status">
      <p className="screen-title">카드가 없습니다</p>
      <p>"새 Task"로 첫 카드를 등록해 보세요.</p>
      <button type="button" onClick={onCreate}>
        새 Task
      </button>
    </div>
  )
}

export function FailedScreen({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="screen screen-failed" role="alert">
      <p className="screen-title">불러오지 못했습니다</p>
      <p>{message}</p>
      <button type="button" onClick={onRetry}>
        다시 시도
      </button>
    </div>
  )
}
