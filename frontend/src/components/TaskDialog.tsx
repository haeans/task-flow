import { useEffect, useRef, useState } from 'react'
import { ApiError, createTask, suggestTask, updateTask } from '../api'
import type { Priority, Task } from '../types'
import { DESCRIPTION_MAX, PRIORITIES, TITLE_MAX } from '../types'
import { validateTaskInput } from '../validate'

interface Props {
  // 있으면 수정, 없으면 새로 등록한다.
  task?: Task
  onClose: () => void
  onSaved: (task: Task) => void
  onNotFound: () => void
  // 로그인이 끝났을 때 (R-010)
  onUnauthorized: () => void
}

const SUGGEST_OFF = '지금은 AI 제안을 쓸 수 없습니다. 직접 입력해 주세요.'
const SUGGEST_FAILED = '제안을 못 받았습니다. 다시 제안 버튼을 눌러 보세요.'

// 새 Task는 별도 입력 창에서 입력한다 (D-012). 수정도 같은 창을 쓴다.
export default function TaskDialog({ task, onClose, onSaved, onNotFound, onUnauthorized }: Props) {
  const ref = useRef<HTMLDialogElement>(null)
  const [title, setTitle] = useState(task?.title ?? '')
  const [description, setDescription] = useState(task?.description ?? '')
  const [priority, setPriority] = useState<Priority>(task?.priority ?? 'NORMAL')
  const [dueDate, setDueDate] = useState(task?.due_date ?? '')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  // AI 제안의 상태. 저장 흐름의 상태(saving, error)와 따로 두어, 제안이 실패해도 저장에 영향이 없다.
  const [suggesting, setSuggesting] = useState(false)
  const [suggestMessage, setSuggestMessage] = useState<string | null>(null)
  const [reason, setReason] = useState<string | null>(null)
  // 창이 닫힌 뒤에 도착한 제안 응답은 버린다.
  const open = useRef(true)

  useEffect(() => {
    open.current = true
    ref.current?.showModal()
    return () => {
      open.current = false
    }
  }, [])

  // 제안은 입력 칸을 채우기만 한다. 저장은 사용자가 등록·저장 버튼을 눌러야 한다 (R-015).
  async function suggest() {
    const invalid = validateTaskInput(title, description, '')
    if (invalid) {
      setSuggestMessage(invalid)
      return
    }
    setSuggesting(true)
    setSuggestMessage(null)
    setReason(null)
    try {
      const s = await suggestTask(title.trim(), description)
      if (!open.current) return
      setPriority(s.priority)
      // 제안에 마감일이 없으면(null) 사용자가 이미 적은 마감일을 지우지 않는다.
      if (s.due_date) setDueDate(s.due_date)
      setReason(s.reason)
    } catch (e) {
      if (!open.current) return
      if (e instanceof ApiError && e.status === 401) {
        onUnauthorized()
        return
      }
      setSuggestMessage(e instanceof ApiError && e.status === 503 ? SUGGEST_OFF : SUGGEST_FAILED)
    } finally {
      if (open.current) setSuggesting(false)
    }
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    const invalid = validateTaskInput(title, description, dueDate)
    if (invalid) {
      setError(invalid)
      return
    }
    setSaving(true)
    setError(null)
    try {
      // 마감일을 비우면 null을 보내 지운다.
      const input = { title: title.trim(), description, priority, due_date: dueDate || null }
      const saved = task ? await updateTask(task.id, input) : await createTask(input)
      onSaved(saved)
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        onUnauthorized()
        return
      }
      if (e instanceof ApiError && e.status === 404) {
        onNotFound()
        return
      }
      setError(
        task
          ? '저장하지 못했습니다. 카드는 바뀌지 않았습니다.'
          : '저장하지 못했습니다. 카드는 만들어지지 않았습니다.',
      )
      setSaving(false)
    }
  }

  return (
    <dialog ref={ref} onClose={onClose} className="dialog">
      <form onSubmit={submit}>
        <h2>{task ? 'Task 수정' : '새 Task'}</h2>
        <label>
          제목
          <input value={title} onChange={(e) => setTitle(e.target.value)} autoFocus />
          <span className="hint">
            {title.trim().length}/{TITLE_MAX}
          </span>
        </label>
        <label>
          설명 (선택)
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={4}
          />
          <span className="hint">
            {description.length}/{DESCRIPTION_MAX}
          </span>
        </label>
        <div className="suggest-row">
          {/* type="button": 눌러도 등록·저장(submit)이 실행되지 않는다. */}
          <button type="button" onClick={suggest} disabled={suggesting}>
            AI 제안
          </button>
          {suggesting && (
            <span role="status" className="suggest-status">
              제안을 받는 중...
            </span>
          )}
          {suggestMessage && (
            <span role="alert" className="error">
              {suggestMessage}
            </span>
          )}
        </div>
        <label>
          우선순위
          <select value={priority} onChange={(e) => setPriority(e.target.value as Priority)}>
            {PRIORITIES.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          마감일 (선택)
          <span className="date-row">
            <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} />
            <button type="button" onClick={() => setDueDate('')} disabled={!dueDate}>
              지우기
            </button>
          </span>
        </label>
        {reason && <p className="suggest-reason">AI 제안 이유: {reason}</p>}
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <div className="actions">
          <button type="button" onClick={() => ref.current?.close()} disabled={saving}>
            취소
          </button>
          <button type="submit" disabled={saving}>
            {saving ? '저장 중...' : task ? '저장' : '등록'}
          </button>
        </div>
      </form>
    </dialog>
  )
}
