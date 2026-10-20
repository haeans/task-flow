import type { Task } from '../types'

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString('ko-KR')
}

export default function TaskCard({ task }: { task: Task }) {
  return (
    <article className="card">
      <h3>{task.title}</h3>
      {task.description && <p className="card-desc">{task.description}</p>}
      <dl className="card-times">
        <dt>생성</dt>
        <dd>{formatTime(task.created_at)}</dd>
        <dt>수정</dt>
        <dd>{formatTime(task.updated_at)}</dd>
      </dl>
    </article>
  )
}
