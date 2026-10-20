import { useEffect, useRef, useState } from 'react'
import { ApiError, createTask, updateTask } from '../api'
import type { Task } from '../types'
import { DESCRIPTION_MAX, TITLE_MAX } from '../types'
import { validateTaskInput } from '../validate'

interface Props {
  // 있으면 수정, 없으면 새로 등록한다.
  task?: Task
  onClose: () => void
  onSaved: (task: Task) => void
  onNotFound: () => void
}

// 새 Task는 별도 입력 창에서 입력한다 (D-012). 수정도 같은 창을 쓴다.
export default function TaskDialog({ task, onClose, onSaved, onNotFound }: Props) {
  const ref = useRef<HTMLDialogElement>(null)
  const [title, setTitle] = useState(task?.title ?? '')
  const [description, setDescription] = useState(task?.description ?? '')
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    ref.current?.showModal()
  }, [])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    const invalid = validateTaskInput(title, description)
    if (invalid) {
      setError(invalid)
      return
    }
    setSaving(true)
    setError(null)
    try {
      const saved = task
        ? await updateTask(task.id, title.trim(), description)
        : await createTask(title.trim(), description)
      onSaved(saved)
    } catch (e) {
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
