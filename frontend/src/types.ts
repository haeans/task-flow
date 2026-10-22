export type Status = 'TODO' | 'IN_PROGRESS' | 'DONE'

export interface Task {
  id: number
  title: string
  description: string
  status: Status
  created_at: string
  updated_at: string
}

export const STATUSES: { value: Status; label: string }[] = [
  { value: 'TODO', label: '할 일' },
  { value: 'IN_PROGRESS', label: '진행 중' },
  { value: 'DONE', label: '완료' },
]

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
