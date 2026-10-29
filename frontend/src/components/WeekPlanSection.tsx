import { planRows, useWeekPlan } from '../useWeekPlan'
import { WEEKPLAN_EMPTY } from '../errors'
import type { Task } from '../types'
import WeekPlanCard from './WeekPlanCard'

interface Props {
  tasks: Task[]
  // 로그인이 끝났을 때 (R-010)
  onUnauthorized: () => void
}

// [오늘 브리핑] 바로 아래의 [이번 주 계획] 버튼과 결과 카드 (R-019, D-038).
export default function WeekPlanSection({ tasks, onUnauthorized }: Props) {
  const { loading, plan, message, make, close } = useWeekPlan(onUnauthorized)
  const rows = plan ? planRows(plan, tasks) : []

  return (
    <div className="weekplan">
      {/* type="button": 눌러도 등록·저장(submit)이 실행되지 않는다. */}
      <button type="button" onClick={make} disabled={loading}>
        {loading ? '나누는 중…' : '이번 주 계획'}
      </button>
      {message && (
        <p role={message.error ? 'alert' : 'status'} className={message.error ? 'error' : 'info'}>
          {message.text}
        </p>
      )}
      {/* 목록에서 찾은 제목이 하나도 없으면 빈 카드 대신 빈 문구를 보인다. */}
      {plan && rows.length === 0 && (
        <p role="status" className="info">
          {WEEKPLAN_EMPTY}
        </p>
      )}
      {plan && rows.length > 0 && <WeekPlanCard rows={rows} note={plan.note} onClose={close} />}
    </div>
  )
}
