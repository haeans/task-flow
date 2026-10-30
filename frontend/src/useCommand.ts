import { useEffect, useRef, useState } from 'react'
import { ApiError, changeStatus, CommandError, createTask, requestCommand, updateTask } from './api'
import type { CommandAction, Task } from './types'

export const COMMAND_OFF = '지금은 시킬 수 없습니다'
export const COMMAND_FAILED = '알아듣지 못했습니다'
const APPLY_FAILED_NONE = '적용하지 못했습니다. 카드는 그대로입니다.'

function applyPartialMessage(total: number, done: number): string {
  return `${total}개 중 ${done}개를 적용했습니다. 남은 ${total - done}개는 [적용]을 다시 눌러 주세요.`
}

// 요청이 실패한 원인을 문구로 바꾼다. 422는 서버가 준 이유 그대로, 그 밖의 서버 응답 내용은 담지 않는다.
function commandErrorMessage(e: unknown): string {
  if (e instanceof CommandError && e.status === 422 && e.detail) return e.detail
  if (e instanceof ApiError && e.status === 503) return COMMAND_OFF
  return COMMAND_FAILED
}

interface Message {
  text: string
  error: boolean
}

// 카드 한 줄이 가리키는 Task를 지금 목록에서 찾는다. add는 Task가 없다.
function taskOf(action: CommandAction, tasks: Task[]): Task | undefined {
  return tasks.find((t) => t.id === action.id)
}

// 확인 카드의 한 장을 기존 API 한 번으로 적용한다. due는 다른 값을 지금 그대로 보낸다
// (PUT은 설명을 빼면 지워지므로 현재 제목·설명·우선순위를 함께 보낸다).
async function applyOne(action: CommandAction, tasks: Task[]): Promise<void> {
  if (action.kind === 'add') {
    await createTask({
      title: action.title,
      description: '',
      priority: action.priority ?? 'NORMAL',
      due_date: action.due_date,
    })
    return
  }
  const task = taskOf(action, tasks)
  if (!task || action.id === null) throw new Error('대상 카드가 목록에 없다')
  if (action.kind === 'due') {
    await updateTask(task.id, {
      title: task.title,
      description: task.description,
      priority: task.priority,
      due_date: action.due_date,
    })
  } else {
    await changeStatus(task.id, 'DONE')
  }
}

// 한 문장으로 시키기의 상태 (#33). 요청한 결과(카드)는 화면에만 두고, [적용]을 눌러야 기존 API로 반영한다.
export function useCommand(tasks: Task[], onUnauthorized: () => void, onApplied: () => void) {
  const [text, setText] = useState('')
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState(false)
  const [actions, setActions] = useState<CommandAction[] | null>(null)
  const [ask, setAsk] = useState<string | null>(null)
  const [message, setMessage] = useState<Message | null>(null)
  // 화면이 사라진 뒤(로그아웃 등)에 도착한 응답은 버린다.
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  function reset() {
    setActions(null)
    setAsk(null)
    setMessage(null)
  }

  async function submit() {
    const sentence = text.trim()
    if (!sentence) return
    setLoading(true)
    reset()
    try {
      const res = await requestCommand(sentence)
      if (!mounted.current) return
      if (res.ask !== null) {
        setAsk(res.ask)
        return
      }
      // 목록에 없는 id를 가리키는 due·done은 적용할 수 없으므로 카드에서 뺀다.
      const usable = res.actions.filter((a) => a.kind === 'add' || taskOf(a, tasks))
      if (usable.length === 0) {
        setMessage({ text: COMMAND_FAILED, error: true })
      } else {
        setActions(usable)
      }
    } catch (e) {
      if (!mounted.current) return
      if (e instanceof ApiError && e.status === 401) {
        onUnauthorized()
        return
      }
      setMessage({ text: commandErrorMessage(e), error: true })
    } finally {
      if (mounted.current) setLoading(false)
    }
  }

  // 카드 순서대로 한 장씩 적용한다. 실패하면 멈추고, 실패한 장부터 카드에 남긴다.
  async function apply() {
    if (!actions) return
    setApplying(true)
    setMessage(null)
    let done = 0
    let unauthorized = false
    try {
      for (const action of actions) {
        await applyOne(action, tasks)
        done += 1
      }
    } catch (e) {
      unauthorized = e instanceof ApiError && e.status === 401
    }
    if (done > 0) onApplied() // 순서가 바뀌었을 수 있으니 목록을 다시 받는다.
    if (!mounted.current) return
    setApplying(false)
    if (unauthorized) {
      onUnauthorized()
      return
    }
    if (done === actions.length) {
      reset()
      setText('')
    } else {
      setActions(actions.slice(done))
      setMessage({
        text: done === 0 ? APPLY_FAILED_NONE : applyPartialMessage(actions.length, done),
        error: true,
      })
    }
  }

  function cancel() {
    reset()
  }

  return { text, setText, loading, applying, actions, ask, message, submit, apply, cancel }
}
