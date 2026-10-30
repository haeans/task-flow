import type { PlanRow } from '../useWeekPlan'

const WEEKDAYS = ['일', '월', '화', '수', '목', '금', '토']

// YYYY-MM-DD를 「MM-DD (요일)」로 바꾼다. 시간대 때문에 하루가 밀리지 않도록 연·월·일로 쪼개 계산한다.
function dayLabel(date: string): string {
  const [y, m, d] = date.split('-').map(Number)
  const weekday = WEEKDAYS[new Date(y, m - 1, d).getDay()]
  return `${String(m).padStart(2, '0')}-${String(d).padStart(2, '0')} (${weekday})`
}

interface Props {
  rows: PlanRow[]
  note: string
  onClose: () => void
}

// 이번 주 계획 카드 (R-019, D-038). 요일별로 그날 할 일 제목을 보여 준다.
export default function WeekPlanCard({ rows, note, onClose }: Props) {
  return (
    <section className="weekplan-card" aria-label="이번 주 계획">
      <h3>이번 주 계획</h3>
      <dl className="weekplan-days">
        {rows.map((r) => (
          <div className="weekplan-day" key={r.date}>
            <dt>{dayLabel(r.date)}</dt>
            <dd>{r.titles.join(' · ')}</dd>
          </div>
        ))}
      </dl>
      <p className="weekplan-note">{note}</p>
      <div className="actions">
        <button type="button" onClick={onClose}>
          닫기
        </button>
      </div>
    </section>
  )
}
