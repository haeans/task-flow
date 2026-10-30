import type { FormEvent } from 'react'
import { useCommand } from '../useCommand'
import { COMMAND_TEXT_MAX, PRIORITIES } from '../types'
import type { CommandAction, Task } from '../types'

interface Props {
  tasks: Task[]
  // 로그인이 끝났을 때 (R-010)
  onUnauthorized: () => void
  // 적용이 끝나 목록을 다시 받을 때
  onApplied: () => void
}

const priorityLabel = (p: string | null) => PRIORITIES.find((x) => x.value === p)?.label ?? '보통'

// 카드 한 줄: 「제목」 — 하려는 일.
function line(a: CommandAction): string {
  if (a.kind === 'add') {
    const due = a.due_date ? `마감 ${a.due_date}` : '마감 없음'
    return `새 카드 「${a.title}」 — 우선순위 ${priorityLabel(a.priority)} · ${due}`
  }
  if (a.kind === 'due') return `「${a.title}」 — 마감 ${a.due_date} 으로`
  return `「${a.title}」 — 완료로`
}

// [이번 주 계획] 아래의 입력란과 [시키기] 단추, 확인 카드 (#33).
export default function CommandSection({ tasks, onUnauthorized, onApplied }: Props) {
  const { text, setText, loading, applying, actions, ask, message, submit, apply, cancel } =
    useCommand(tasks, onUnauthorized, onApplied)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    submit()
  }

  return (
    <div className="command">
      <form className="command-form" onSubmit={handleSubmit}>
        <input
          type="text"
          aria-label="한 문장으로 시키기"
          placeholder="예: 내일까지 보고서 쓰기 추가해 줘"
          maxLength={COMMAND_TEXT_MAX}
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={loading || applying}
        />
        <button type="submit" disabled={loading || applying || text.trim() === ''}>
          {loading ? '알아듣는 중…' : '시키기'}
        </button>
      </form>
      {message && (
        <p role={message.error ? 'alert' : 'status'} className={message.error ? 'error' : 'info'}>
          {message.text}
        </p>
      )}
      {ask !== null && (
        <p role="status" className="info">
          {ask}
        </p>
      )}
      {actions && (
        <section className="command-card" aria-label="확인">
          <h3>이렇게 바꿀까요? {actions.length}개</h3>
          <ul>
            {actions.map((a, i) => (
              <li key={i}>{line(a)}</li>
            ))}
          </ul>
          <div className="actions">
            <button type="button" onClick={cancel} disabled={applying}>
              취소
            </button>
            <button type="button" onClick={apply} disabled={applying}>
              {applying ? '적용하는 중…' : '적용'}
            </button>
          </div>
        </section>
      )}
    </div>
  )
}
