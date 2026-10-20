import { STATUSES, type Status, type Task } from '../types'
import Column from './Column'

interface Props {
  tasks: Task[]
  onChangeStatus: (id: number, status: Status) => void
}

export default function Board({ tasks, onChangeStatus }: Props) {
  return (
    <div className="board">
      {STATUSES.map(({ value, label }) => (
        <Column
          key={value}
          status={value}
          label={label}
          tasks={tasks.filter((t) => t.status === value)}
          onChangeStatus={onChangeStatus}
        />
      ))}
    </div>
  )
}
