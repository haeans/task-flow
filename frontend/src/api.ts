import type {
  Briefing,
  CommandResult,
  Status,
  Suggestion,
  Task,
  TaskDraft,
  TaskInput,
  User,
  WeekPlan,
} from './types'

export const NETWORK_ERROR = '서버에 연결하지 못했습니다.'

// 서버가 준 오류. status 0은 서버에 닿지 못한 경우이다.
// detail은 서버가 문장으로 준 이유이다. 422 입력 오류처럼 문장이 아니면 null이다.
export class ApiError extends Error {
  status: number
  detail: string | null

  constructor(status: number, detail: string | null = null, message?: string) {
    super(message ?? detail ?? `요청 실패 (${status})`)
    this.status = status
    this.detail = detail
  }
}

// 401(로그인하지 않았거나 로그인이 끝남)이면 부르는 자리이다. 로그인 화면으로 돌리는 일은 App이 등록한다.
let onUnauthorized: (() => void) | null = null

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler
}

async function request<T>(path: string, init?: RequestInit, notifyUnauthorized = true): Promise<T> {
  let res: Response
  try {
    res = await fetch(`/api${path}`, init)
  } catch {
    throw new ApiError(0, null, NETWORK_ERROR)
  }
  if (!res.ok) {
    let detail: string | null = null
    try {
      const body = await res.json()
      if (typeof body?.detail === 'string') detail = body.detail
    } catch {
      // 본문을 읽지 못하면 상태 코드만 담는다.
    }
    if (res.status === 401 && notifyUnauthorized) onUnauthorized?.()
    throw new ApiError(res.status, detail)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export function listTasks(): Promise<Task[]> {
  return request<Task[]>('/tasks')
}

export function createTask(input: TaskInput): Promise<Task> {
  return request<Task>('/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
}

// due_date가 null이면 마감일을 지운다 (R-012).
export function updateTask(id: number, input: TaskInput): Promise<Task> {
  return request<Task>(`/tasks/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
}

// 제목·설명으로 우선순위와 마감일을 제안받는다 (R-015). 저장하지 않는다.
export function suggestTask(title: string, description: string): Promise<Suggestion> {
  return request<Suggestion>('/tasks/suggest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, description }),
  })
}

// 제목(주제)·설명으로 할 일 초안 3~5개를 받는다 (R-016). 저장하지 않는다.
export async function suggestDrafts(title: string, description: string): Promise<TaskDraft[]> {
  const res = await request<{ tasks: TaskDraft[] }>('/tasks/suggestions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, description }),
  })
  return res.tasks
}

// 완료가 아닌 내 할 일로 오늘의 브리핑을 받는다 (R-018). 본문이 없고 저장하지 않는다.
export function requestBriefing(): Promise<Briefing> {
  return request<Briefing>('/tasks/briefing', { method: 'POST' })
}

// 완료가 아닌 내 할 일을 오늘부터 일주일에 나눈 계획을 받는다 (R-019). 본문이 없고 저장하지 않는다.
export function requestWeekPlan(): Promise<WeekPlan> {
  return request<WeekPlan>('/tasks/weekplan', { method: 'POST' })
}

export function deleteTask(id: number): Promise<void> {
  return request<void>(`/tasks/${id}`, { method: 'DELETE' })
}

// 버튼·선택 메뉴와 드래그가 같은 요청을 쓴다 (D-004).
export function changeStatus(id: number, status: Status): Promise<Task> {
  return request<Task>(`/tasks/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
}

// 가입 뒤 자동으로 로그인하지 않는다. 로그인은 따로 한다 (D-026).
export function signup(username: string, password: string): Promise<User> {
  return request<User>('/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
}

// 로그인 상태는 서버가 내려 주는 쿠키(HttpOnly)가 들고 있다. 화면은 값을 다루지 않는다.
export function login(username: string, password: string): Promise<User> {
  // 비밀번호가 틀려도 401이므로 로그인 화면으로 돌리는 자리는 부르지 않는다.
  return request<User>(
    '/sessions',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    },
    false,
  )
}

export function logout(): Promise<void> {
  return request<void>('/sessions', { method: 'DELETE' })
}

// 한 문장을 actions로 바꿔 받는다 (#33). 저장하지 않는다. 422의 이유는 ApiError.detail에 담긴다.
export function requestCommand(text: string): Promise<CommandResult> {
  return request<CommandResult>('/tasks/command', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
  })
}
