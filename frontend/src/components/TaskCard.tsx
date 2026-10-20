import { STATUSES, type Status, type Task } from '../types'

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString('ko-KR')
}

interface Props {
  task: Task
  onChangeStatus: (id: number, status: Status) => void
}

export default function TaskCard({ task, onChangeStatus }: Props) {
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
    </article>
  )
}
