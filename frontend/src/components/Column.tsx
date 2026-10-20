import { useState } from 'react'
import type { Status, Task } from '../types'
import TaskCard from './TaskCard'

interface Props {
  status: Status
  label: string
  tasks: Task[]
  onChangeStatus: (id: number, status: Status) => void
}

export default function Column({ status, label, tasks, onChangeStatus }: Props) {
  const [over, setOver] = useState(false)

  return (
    <section
      className={over ? 'column drop-target' : 'column'}
      data-status={status}
      aria-label={label}
      onDragOver={(e) => {
        e.preventDefault()
        e.dataTransfer.dropEffect = 'move'
        setOver(true)
      }}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setOver(false)
      }}
      onDrop={(e) => {
        e.preventDefault()
        setOver(false)
        const id = Number(e.dataTransfer.getData('text/plain'))
        if (Number.isInteger(id) && !tasks.some((t) => t.id === id)) {
          onChangeStatus(id, status)
        }
      }}
    >
      <h2>
        {label} <span className="count">{tasks.length}</span>
      </h2>
      <div className="cards">
        {tasks.map((task) => (
          <TaskCard key={task.id} task={task} onChangeStatus={onChangeStatus} />
        ))}
      </div>
    </section>
  )
}
