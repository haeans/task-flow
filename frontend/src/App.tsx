import { useCallback, useEffect, useState } from 'react'
import { ApiError, changeStatus, listTasks } from './api'
import Board from './components/Board'
import TaskDialog from './components/TaskDialog'
import type { Status, Task } from './types'

type Load = 'loading' | 'ready' | 'failed'

function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [load, setLoad] = useState<Load>('loading')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

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

  // 성공 응답을 받은 뒤에만 화면에 반영한다 (AQ-001).
  async function handleChangeStatus(id: number, status: Status) {
    setNotice(null)
    try {
      const updated = await changeStatus(id, status)
      setTasks((prev) => prev.map((t) => (t.id === id ? updated : t)))
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) {
        setNotice('카드가 이미 없습니다. 목록을 다시 불러옵니다.')
        fetchTasks()
      } else {
        setNotice('상태를 바꾸지 못했습니다. 카드의 상태는 그대로입니다.')
      }
    }
  }

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
      {notice && (
        <p role="alert" className="error">
          {notice}
        </p>
      )}
      {load === 'ready' && <Board tasks={tasks} onChangeStatus={handleChangeStatus} />}
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
