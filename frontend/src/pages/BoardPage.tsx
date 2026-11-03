import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError, changeStatus, deleteTask, listTasks, logout, setUnauthorizedHandler } from '../api'
import Board from '../components/Board'
import BriefingSection from '../components/BriefingSection'
import CommandSection from '../components/CommandSection'
import Notice from '../components/Notice'
import TaskDialog from '../components/TaskDialog'
import WeekPlanSection from '../components/WeekPlanSection'
import { loadErrorMessage } from '../errors'
import type { Status, Task } from '../types'
import { useLoad } from '../useLoad'
import type { AuthLocationState } from './LoginPage'
import { EmptyScreen, FailedScreen, LoadingScreen, SESSION_ENDED_NOTICE } from './Status'

const NOT_FOUND_NOTICE = '카드가 이미 없습니다. 목록을 다시 불러옵니다.'

export default function BoardPage() {
  const navigate = useNavigate()

  // 처음 불러올 때의 401은 로그인 전이라 안내 없이 로그인 화면으로 보낸다.
  const toLoginQuietly = useCallback(() => navigate('/login', { replace: true }), [navigate])
  const { state, data: tasks, setData: setTasks, error, reload } = useLoad<Task[]>(
    listTasks,
    [],
    toLoginQuietly,
  )
  // 'new'는 등록 창, Task는 그 카드의 수정 창, null은 닫힘.
  const [dialog, setDialog] = useState<Task | 'new' | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  // 카드 요청이 401이면 로그인이 끝난 것이다. 로그인 화면으로 보내면 이 화면의 카드는 사라진다.
  const handleUnauthorized = useCallback(() => {
    const next: AuthLocationState = { notice: SESSION_ENDED_NOTICE }
    navigate('/login', { replace: true, state: next })
  }, [navigate])

  // 목록을 불러온 뒤의 401은 api.ts가 알려 준다.
  useEffect(() => {
    if (state !== 'ready') return
    setUnauthorizedHandler(handleUnauthorized)
    return () => setUnauthorizedHandler(null)
  }, [state, handleUnauthorized])

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
    navigate('/login', { replace: true })
  }

  // 순서는 서버가 정한다 (R-014). 변경은 이미 화면에 반영했으므로, 순서를 맞추려는 재조회가
  // 실패해도 화면은 그대로 둔다. 로그인이 끝난 경우(401)만 로그인 화면으로 보낸다.
  function syncOrder() {
    listTasks()
      .then(setTasks)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) handleUnauthorized()
      })
  }

  function handleNotFound() {
    setDialog(null)
    setNotice(NOT_FOUND_NOTICE)
    reload()
  }

  // 성공 응답을 받은 뒤에만 화면에 반영한다 (AQ-001).
  async function handleChangeStatus(id: number, status: Status) {
    setNotice(null)
    try {
      const updated = await changeStatus(id, status)
      setTasks((prev) => prev.map((t) => (t.id === id ? updated : t)))
      syncOrder() // 완료로 옮기면 기한 초과가 풀려 순서가 바뀐다.
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

  // 모두 등록으로 만들어진 카드들을 보드에 넣는다. 창은 닫지 않는다 (D-033).
  function handleCreatedMany(created: Task[]) {
    setTasks((prev) => {
      const have = new Set(prev.map((t) => t.id))
      return [...created.filter((t) => !have.has(t.id)), ...prev]
    })
    syncOrder()
  }

  function handleSaved(saved: Task) {
    setTasks((prev) =>
      prev.some((t) => t.id === saved.id)
        ? prev.map((t) => (t.id === saved.id ? saved : t))
        : [saved, ...prev],
    )
    setDialog(null)
    syncOrder()
  }

  return (
    <main>
      <header className="top">
        <h1>task-flow</h1>
        <div className="top-actions">
          <button onClick={() => setDialog('new')} disabled={state !== 'ready'}>
            새 Task
          </button>
          <button onClick={handleLogout} disabled={state === 'loading'}>
            로그아웃
          </button>
        </div>
      </header>
      {notice && <Notice message={notice} onDismiss={() => setNotice(null)} />}
      {state === 'loading' && <LoadingScreen />}
      {state === 'failed' && <FailedScreen message={loadErrorMessage(error)} onRetry={reload} />}
      {state === 'ready' && (
        <>
          {tasks.length === 0 && <EmptyScreen onCreate={() => setDialog('new')} />}
          <BriefingSection tasks={tasks} onUnauthorized={handleUnauthorized} />
          <WeekPlanSection tasks={tasks} onUnauthorized={handleUnauthorized} />
          <CommandSection tasks={tasks} onUnauthorized={handleUnauthorized} onApplied={syncOrder} />
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
          onCreatedMany={handleCreatedMany}
          onNotFound={handleNotFound}
          onUnauthorized={handleUnauthorized}
        />
      )}
    </main>
  )
}
