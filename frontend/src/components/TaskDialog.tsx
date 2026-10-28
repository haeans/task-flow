import { useEffect, useRef, useState } from 'react'
import { ApiError, createTask, suggestDrafts, suggestTask, updateTask } from '../api'
import { REGISTER_FAILED_NONE, draftErrorMessage, registerPartialMessage } from '../errors'
import type { Priority, Task, TaskDraft } from '../types'
import { DESCRIPTION_MAX, PRIORITIES, TITLE_MAX } from '../types'
import { validateTaskInput } from '../validate'
import DraftPreview from './DraftPreview'

interface Props {
  // 있으면 수정, 없으면 새로 등록한다.
  task?: Task
  onClose: () => void
  onSaved: (task: Task) => void
  // 모두 등록으로 만들어진 카드들을 보드에 넣는다. 창은 닫지 않는다 (D-033).
  onCreatedMany: (tasks: Task[]) => void
  onNotFound: () => void
  // 로그인이 끝났을 때 (R-010)
  onUnauthorized: () => void
}

const SUGGEST_OFF = '지금은 AI 제안을 쓸 수 없습니다. 직접 입력해 주세요.'
const SUGGEST_FAILED = '제안을 못 받았습니다. 다시 제안 버튼을 눌러 보세요.'

// 새 Task는 별도 입력 창에서 입력한다 (D-012). 수정도 같은 창을 쓴다.
export default function TaskDialog({
  task,
  onClose,
  onSaved,
  onCreatedMany,
  onNotFound,
  onUnauthorized,
}: Props) {
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
  // AI 할 일 초안 (R-016). 이것도 저장 흐름과 AI 제안의 상태와 따로 둔다.
  const [drafts, setDrafts] = useState<TaskDraft[] | null>(null)
  const [drafting, setDrafting] = useState(false)
  const [draftMessage, setDraftMessage] = useState<string | null>(null)
  // 모두 등록 중이면 진행 상황. 아니면 null.
  const [registering, setRegistering] = useState<{ done: number; total: number } | null>(null)
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

  // 제목(주제)과 설명으로 초안을 받아 미리보기만 보여 준다. 입력 칸은 건드리지 않고 저장하지 않는다 (R-016).
  async function makeDrafts() {
    const invalid = validateTaskInput(title, description, '')
    if (invalid) {
      setDraftMessage(invalid)
      return
    }
    setDrafting(true)
    setDraftMessage(null)
    setDrafts(null)
    try {
      const made = await suggestDrafts(title.trim(), description)
      if (!open.current) return
      setDrafts(made)
    } catch (e) {
      if (!open.current) return
      if (e instanceof ApiError && e.status === 401) {
        onUnauthorized()
        return
      }
      setDraftMessage(draftErrorMessage(e))
    } finally {
      if (open.current) setDrafting(false)
    }
  }

  // 기존 등록(createTask)을 초안마다 순서대로 한 번씩 부른다. 하나라도 실패하면 거기서 멈추고,
  // 성공한 초안은 보드에 두고 남은 초안만 미리보기에 남긴다 (D-033).
  async function registerAll() {
    if (!drafts) return
    const queue = drafts
    const created: Task[] = []
    setDraftMessage(null)
    setRegistering({ done: 0, total: queue.length })
    try {
      for (const d of queue) {
        const saved = await createTask({
          title: d.title,
          description: '',
          priority: d.priority,
          due_date: d.due_date,
        })
        created.push(saved)
        if (open.current) setRegistering({ done: created.length, total: queue.length })
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        onUnauthorized()
        return
      }
      if (created.length) onCreatedMany(created)
      if (!open.current) return
      setDrafts(queue.slice(created.length))
      setDraftMessage(
        created.length ? registerPartialMessage(queue.length, created.length) : REGISTER_FAILED_NONE,
      )
      setRegistering(null)
      return
    }
    onCreatedMany(created)
    ref.current?.close()
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
    // 모두 등록 중에는 Esc로 창이 닫히지 않게 한다 (D-033).
    <dialog
      ref={ref}
      onClose={onClose}
      onCancel={(e) => {
        if (registering) e.preventDefault()
      }}
      className="dialog"
    >
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
          <button type="button" onClick={suggest} disabled={suggesting || drafting || !!registering}>
            AI 제안
          </button>
          {!task && (
            <button type="button" onClick={makeDrafts} disabled={drafting || !!registering || saving}>
              AI로 할 일 만들기
            </button>
          )}
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
        {!task && (
          <p className="draft-hint">제목에 주제를 적으면 할 일 3~5개를 만들어 보여 줍니다.</p>
        )}
        {drafting && (
          <p role="status" className="suggest-status">
            만드는 중...
          </p>
        )}
        {draftMessage && (
          <p role="alert" className="error">
            {draftMessage}
          </p>
        )}
        {!task && drafts && (
          <DraftPreview
            drafts={drafts}
            busy={!!registering}
            progress={
              registering ? `등록 중... (${registering.done}/${registering.total})` : null
            }
            onRegisterAll={registerAll}
            onCancel={() => {
              setDrafts(null)
              setDraftMessage(null)
            }}
          />
        )}
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
          <button type="button" onClick={() => ref.current?.close()} disabled={saving || !!registering}>
            취소
          </button>
          <button type="submit" disabled={saving || drafting || !!registering}>
            {saving ? '저장 중...' : task ? '저장' : '등록'}
          </button>
        </div>
      </form>
    </dialog>
  )
}
