import type { Status, Task } from './types'

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
  return res.json() as Promise<T>
}

export function listTasks(): Promise<Task[]> {
  return request<Task[]>('/tasks')
}

export function createTask(title: string, description: string): Promise<Task> {
  return request<Task>('/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, description }),
  })
}

// 버튼·선택 메뉴와 드래그가 같은 요청을 쓴다 (D-004).
export function changeStatus(id: number, status: Status): Promise<Task> {
  return request<Task>(`/tasks/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
}
