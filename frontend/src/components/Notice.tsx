// 등록·수정·상태 변경·삭제가 실패했을 때의 알림. 카드는 바뀌지 않았음을 알린다.
export default function Notice({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div className="notice" role="alert">
      <span>{message}</span>
      <button type="button" onClick={onDismiss} aria-label="알림 닫기">
        닫기
      </button>
    </div>
  )
}
