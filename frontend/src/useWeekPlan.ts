import { useEffect, useRef, useState } from 'react'
import { ApiError, requestWeekPlan } from './api'
import { WEEKPLAN_EMPTY, weekPlanErrorMessage } from './errors'
import type { Task, WeekPlan } from './types'

interface Message {
  text: string
  error: boolean
}

export interface PlanRow {
  date: string
  titles: string[]
}

// 서버는 id만 주므로 제목은 지금 목록에서 id로 찾는다. 목록에 없는 id는 건너뛰고,
// 제목이 하나도 남지 않은 날은 줄에서 뺀다 (D-038).
export function planRows(plan: WeekPlan, tasks: Task[]): PlanRow[] {
  const titleOf = new Map(tasks.map((t) => [t.id, t.title]))
  return plan.days
    .map((d) => ({
      date: d.date,
      titles: d.task_ids.flatMap((id) => titleOf.get(id) ?? []),
    }))
    .filter((r) => r.titles.length > 0)
}

// 이번 주 계획 요청의 상태 (R-019, D-038). 저장하지 않고, 받은 결과는 화면에만 둔다.
export function useWeekPlan(onUnauthorized: () => void) {
  const [loading, setLoading] = useState(false)
  const [plan, setPlan] = useState<WeekPlan | null>(null)
  const [message, setMessage] = useState<Message | null>(null)
  // 화면이 사라진 뒤(로그아웃 등)에 도착한 응답은 버린다.
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
    }
  }, [])

  async function make() {
    setLoading(true)
    setMessage(null)
    setPlan(null)
    try {
      const p = await requestWeekPlan()
      if (!mounted.current) return
      // 완료가 아닌 할 일이 0개이면 서버가 빈 days로 200을 준다. 서버 문구에 기대지 않는다.
      if (p.days.length === 0) {
        setMessage({ text: WEEKPLAN_EMPTY, error: false })
      } else {
        setPlan(p)
      }
    } catch (e) {
      if (!mounted.current) return
      if (e instanceof ApiError && e.status === 401) {
        onUnauthorized()
        return
      }
      setMessage({ text: weekPlanErrorMessage(e), error: true })
    } finally {
      if (mounted.current) setLoading(false)
    }
  }

  function close() {
    setPlan(null)
    setMessage(null)
  }

  return { loading, plan, message, make, close }
}
