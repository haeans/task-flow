import { STATUSES, type Status, type Task } from '../types'
import Column from './Column'

interface Props {
  tasks: Task[]
  onChangeStatus: (id: number, status: Status) => void
  onEdit: (task: Task) => void
  onDelete: (task: Task) => void
}

export default function Board({ tasks, onChangeStatus, onEdit, onDelete }: Props) {
  return (
    <div className="board">
      {STATUSES.map(({ value, label }) => (
        <Column
          key={value}
          status={value}
          label={label}
          tasks={tasks.filter((t) => t.status === value)}
          onChangeStatus={onChangeStatus}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </div>
  )
}
