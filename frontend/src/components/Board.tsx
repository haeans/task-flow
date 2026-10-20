import { STATUSES, type Task } from '../types'
import Column from './Column'

export default function Board({ tasks }: { tasks: Task[] }) {
  return (
    <div className="board">
      {STATUSES.map(({ value, label }) => (
        <Column
          key={value}
          status={value}
          label={label}
          tasks={tasks.filter((t) => t.status === value)}
        />
      ))}
    </div>
  )
}
