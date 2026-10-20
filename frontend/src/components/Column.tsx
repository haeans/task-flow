import type { Status, Task } from '../types'
import TaskCard from './TaskCard'

interface Props {
  status: Status
  label: string
  tasks: Task[]
}

export default function Column({ status, label, tasks }: Props) {
  return (
    <section className="column" data-status={status} aria-label={label}>
      <h2>
        {label} <span className="count">{tasks.length}</span>
      </h2>
      <div className="cards">
        {tasks.map((task) => (
          <TaskCard key={task.id} task={task} />
        ))}
      </div>
    </section>
  )
}
