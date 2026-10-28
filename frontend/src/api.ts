import type { Status, Suggestion, Task, TaskInput, User } from './types'

export class ApiError extends Error {
  status: number

  constructor(status: number) {
    super(`요청 실패 (${status})`)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, init)
  if (!res.ok) throw new ApiError(res.status)
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
  return request<User>('/sessions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
}

export function logout(): Promise<void> {
  return request<void>('/sessions', { method: 'DELETE' })
}
