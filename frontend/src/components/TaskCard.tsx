import { PRIORITIES, STATUSES, type Status, type Task } from '../types'

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString('ko-KR')
}

interface Props {
  task: Task
  onChangeStatus: (id: number, status: Status) => void
  onEdit: (task: Task) => void
  onDelete: (task: Task) => void
}

export default function TaskCard({ task, onChangeStatus, onEdit, onDelete }: Props) {
  return (
    <article
      className="card"
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData('text/plain', String(task.id))
        e.dataTransfer.effectAllowed = 'move'
      }}
    >
      <h3>{task.title}</h3>
      {task.description && <p className="card-desc">{task.description}</p>}
      {/* 마감일은 사용자가 정하는 값이라 시스템 시각(생성·수정)과 따로 보여 준다. */}
      <div className="card-meta">
        <span className={`badge priority-${task.priority.toLowerCase()}`}>
          우선순위 {PRIORITIES.find((p) => p.value === task.priority)?.label}
        </span>
        {task.due_date && <span className="due">마감 {task.due_date}</span>}
        {task.overdue && <span className="badge overdue">기한 초과</span>}
      </div>
      <dl className="card-times">
        <dt>생성</dt>
        <dd>{formatTime(task.created_at)}</dd>
        <dt>수정</dt>
        <dd>{formatTime(task.updated_at)}</dd>
      </dl>
      <label className="card-status">
        상태
        <select
          value={task.status}
          onChange={(e) => onChangeStatus(task.id, e.target.value as Status)}
        >
          {STATUSES.map(({ value, label }) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <div className="card-actions">
        <button type="button" onClick={() => onEdit(task)}>
          수정
        </button>
        <button type="button" onClick={() => onDelete(task)}>
          삭제
        </button>
      </div>
    </article>
  )
}
