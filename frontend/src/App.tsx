import { useCallback, useEffect, useState } from 'react'
import { ApiError, changeStatus, deleteTask, listTasks, logout } from './api'
import AuthScreen from './components/AuthScreen'
import Board from './components/Board'
import Notice from './components/Notice'
import { EmptyScreen, FailedScreen, LoadingScreen } from './components/StatusScreen'
import TaskDialog from './components/TaskDialog'
import { loadErrorMessage } from './errors'
import type { Status, Task } from './types'

// loggedOut: 로그인하지 않았거나 로그아웃했거나 로그인이 끝난 상태 (B-5). 카드를 보여 주지 않는다.
type Load = 'loading' | 'ready' | 'failed' | 'loggedOut'

const NOT_FOUND_NOTICE = '카드가 이미 없습니다. 목록을 다시 불러옵니다.'
const SESSION_ENDED_NOTICE = '로그인이 끝났습니다. 다시 로그인하세요.'

function App() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [load, setLoad] = useState<Load>('loading')
  // 'new'는 등록 창, Task는 그 카드의 수정 창, null은 닫힘.
  const [dialog, setDialog] = useState<Task | 'new' | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loadError, setLoadError] = useState('')
  const [authNotice, setAuthNotice] = useState<string | null>(null)

  const fetchTasks = useCallback(() => {
    listTasks()
      .then((list) => {
        setTasks(list)
        setLoad('ready')
      })
      .catch((e) => {
        // 새로고침했을 때 로그인 상태는 목록 요청의 401/200으로 안다.
        if (e instanceof ApiError && e.status === 401) {
          setTasks([])
          setLoad('loggedOut')
          return
        }
        setLoadError(loadErrorMessage(e))
        setLoad('failed')
      })
  }, [])

  const retry = () => {
    setLoad('loading')
    fetchTasks()
  }

  useEffect(fetchTasks, [fetchTasks])

  // 카드 요청이 401이면 로그인이 끝난 것이다. 화면의 카드를 지우고 로그인 화면으로 보낸다.
  function handleUnauthorized() {
    setDialog(null)
    setNotice(null)
    setTasks([])
    setAuthNotice(SESSION_ENDED_NOTICE)
    setLoad('loggedOut')
  }

  function handleLoggedIn() {
    setAuthNotice(null)
    setLoad('loading')
    fetchTasks()
  }

  async function handleLogout() {
    setNotice(null)
    try {
      await logout()
    } catch (e) {
      // 이미 로그인이 끝난 상태(401)면 결과는 같다. 그 밖의 실패는 로그아웃되지 않은 채로 알린다.
      if (!(e instanceof ApiError && e.status === 401)) {
        setNotice('로그아웃하지 못했습니다. 로그인 상태는 그대로입니다.')
        return
      }
    }
    setDialog(null)
    setTasks([])
    setAuthNotice(null)
    setLoad('loggedOut')
  }

  function handleNotFound() {
    setDialog(null)
    setNotice(NOT_FOUND_NOTICE)
    fetchTasks()
  }

  // 성공 응답을 받은 뒤에만 화면에 반영한다 (AQ-001).
  async function handleChangeStatus(id: number, status: Status) {
    setNotice(null)
    try {
      const updated = await changeStatus(id, status)
      setTasks((prev) => prev.map((t) => (t.id === id ? updated : t)))
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        handleUnauthorized()
      } else if (e instanceof ApiError && e.status === 404) {
        handleNotFound()
      } else {
        setNotice('상태를 바꾸지 못했습니다. 카드의 상태는 그대로입니다.')
      }
    }
  }

  // 삭제 전에 한 번 묻는다 (D-013). 취소하면 요청을 보내지 않는다.
  async function handleDelete(task: Task) {
    if (!window.confirm(`"${task.title}" 카드를 삭제할까요? 삭제하면 복구할 수 없습니다.`)) {
      return
    }
    setNotice(null)
    try {
      await deleteTask(task.id)
      setTasks((prev) => prev.filter((t) => t.id !== task.id))
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        handleUnauthorized()
      } else if (e instanceof ApiError && e.status === 404) {
        handleNotFound()
      } else {
        setNotice('삭제하지 못했습니다. 카드는 그대로입니다.')
      }
    }
  }

  function handleSaved(saved: Task) {
    setTasks((prev) =>
      prev.some((t) => t.id === saved.id)
        ? prev.map((t) => (t.id === saved.id ? saved : t))
        : [saved, ...prev],
    )
    setDialog(null)
  }

  return (
    <main>
      <header className="top">
        <h1>task-flow</h1>
        {load !== 'loggedOut' && (
          <div className="top-actions">
            <button onClick={() => setDialog('new')} disabled={load !== 'ready'}>
              새 Task
            </button>
            <button onClick={handleLogout} disabled={load === 'loading'}>
              로그아웃
            </button>
          </div>
        )}
      </header>
      {notice && <Notice message={notice} onDismiss={() => setNotice(null)} />}
      {load === 'loggedOut' && <AuthScreen notice={authNotice} onLoggedIn={handleLoggedIn} />}
      {load === 'loading' && <LoadingScreen />}
      {load === 'failed' && <FailedScreen message={loadError} onRetry={retry} />}
      {load === 'ready' && (
        <>
          {tasks.length === 0 && <EmptyScreen onCreate={() => setDialog('new')} />}
          <Board
            tasks={tasks}
            onChangeStatus={handleChangeStatus}
            onEdit={setDialog}
            onDelete={handleDelete}
          />
        </>
      )}
      {dialog && (
        <TaskDialog
          key={dialog === 'new' ? 'new' : dialog.id}
          task={dialog === 'new' ? undefined : dialog}
          onClose={() => setDialog(null)}
          onSaved={handleSaved}
          onNotFound={handleNotFound}
          onUnauthorized={handleUnauthorized}
        />
      )}
    </main>
  )
}

export default App
