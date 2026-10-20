import { useCallback, useEffect, useState } from 'react'
import { listTasks } from './api'
import Board from './components/Board'
import TaskDialog from './components/TaskDialog'
import type { Task } from './types'

type Load = 'loading' | 'ready' | 'failed'

function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [load, setLoad] = useState<Load>('loading')
  const [dialogOpen, setDialogOpen] = useState(false)

  const fetchTasks = useCallback(() => {
    listTasks()
      .then((list) => {
        setTasks(list)
        setLoad('ready')
      })
      .catch(() => setLoad('failed'))
  }, [])

  const retry = () => {
    setLoad('loading')
    fetchTasks()
  }

  useEffect(fetchTasks, [fetchTasks])

  return (
    <main>
      <header className="top">
        <h1>task-flow</h1>
        <button onClick={() => setDialogOpen(true)} disabled={load !== 'ready'}>
          새 Task
        </button>
      </header>
      {load === 'loading' && <p>불러오는 중...</p>}
      {load === 'failed' && (
        <p role="alert" className="error">
          카드를 불러오지 못했습니다. <button onClick={retry}>다시 시도</button>
        </p>
      )}
      {load === 'ready' && <Board tasks={tasks} />}
      {dialogOpen && (
        <TaskDialog
          onClose={() => setDialogOpen(false)}
          onCreated={(task) => {
            setTasks((prev) => [task, ...prev])
            setDialogOpen(false)
          }}
        />
      )}
    </main>
  )
}

export default App
