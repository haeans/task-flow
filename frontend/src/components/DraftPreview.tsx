import type { TaskDraft } from '../types'
import { PRIORITIES } from '../types'

interface Props {
  drafts: TaskDraft[]
  busy: boolean
  // 등록 중일 때 "등록 중... (k/n)" 같은 진행 문구. 아니면 null.
  progress: string | null
  onRegisterAll: () => void
  onCancel: () => void
}

// AI가 만든 할 일 미리보기 (R-016, D-033). 저장된 카드가 아니라서 항목에는 수정·삭제 조작이 없다.
export default function DraftPreview({ drafts, busy, progress, onRegisterAll, onCancel }: Props) {
  return (
    <section className="draft-preview" aria-label="AI가 만든 할 일 미리보기">
      <h3>AI가 만든 할 일 {drafts.length}개</h3>
      <ul>
        {drafts.map((d, i) => (
          <li key={i}>
            <span className="draft-title">{d.title}</span>
            <span className="draft-meta">
              {PRIORITIES.find((p) => p.value === d.priority)?.label ?? d.priority}
              {' · '}
              {d.due_date ? `마감 ${d.due_date}` : '마감 없음'}
            </span>
          </li>
        ))}
      </ul>
      {progress && (
        <p role="status" className="suggest-status">
          {progress}
        </p>
      )}
      <div className="actions">
        <button type="button" onClick={onCancel} disabled={busy}>
          취소
        </button>
        <button type="button" onClick={onRegisterAll} disabled={busy}>
          모두 등록
        </button>
      </div>
    </section>
  )
}
