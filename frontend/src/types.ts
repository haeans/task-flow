export type Status = 'TODO' | 'IN_PROGRESS' | 'DONE'

export type Priority = 'LOW' | 'NORMAL' | 'HIGH'

export interface Task {
  id: number
  title: string
  description: string
  status: Status
  priority: Priority
  // YYYY-MM-DD. 없으면 null. 시각이 아니라 날짜 문자열이므로 시간대 변환 없이 그대로 보여 준다.
  due_date: string | null
  // 서버가 목록을 줄 때 계산한다 (R-013).
  overdue: boolean
  created_at: string
  updated_at: string
}

export const STATUSES: { value: Status; label: string }[] = [
  { value: 'TODO', label: '할 일' },
  { value: 'IN_PROGRESS', label: '진행 중' },
  { value: 'DONE', label: '완료' },
]

export const PRIORITIES: { value: Priority; label: string }[] = [
  { value: 'LOW', label: '낮음' },
  { value: 'NORMAL', label: '보통' },
  { value: 'HIGH', label: '높음' },
]

export interface TaskInput {
  title: string
  description: string
  priority: Priority
  due_date: string | null
}

export const TITLE_MAX = 100
export const DESCRIPTION_MAX = 1000

export interface User {
  id: number
  username: string
}

// API와 같은 기준 (Q-014)
export const USERNAME_PATTERN = /^[A-Za-z0-9]{4,20}$/
export const PASSWORD_MIN = 8
export const PASSWORD_MAX = 100
