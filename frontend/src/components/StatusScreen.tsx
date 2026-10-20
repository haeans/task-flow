// 화면 상태 표시: 불러오는 중, 카드 없음, 실패 (R-009).

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
