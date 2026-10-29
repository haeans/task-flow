import type { Briefing, Task } from '../types'

const NUMBERS = ['①', '②', '③']

interface Props {
  briefing: Briefing
  tasks: Task[]
  onClose: () => void
}

// 오늘 브리핑 카드 (R-018, D-036). 서버는 id만 주므로 제목은 지금 목록에서 id로 찾는다.
// 그사이 삭제되어 목록에 없는 id는 건너뛴다.
export default function BriefingCard({ briefing, tasks, onClose }: Props) {
  const titleOf = new Map(tasks.map((t) => [t.id, t.title]))
  const top = briefing.top3.filter((p) => titleOf.has(p.id))
  const later = briefing.later.filter((id) => titleOf.has(id))

  return (
    <section className="briefing-card" aria-label="오늘 브리핑">
      {top.length > 0 && (
        <>
          <h3>먼저 할 일</h3>
          <ul>
            {top.map((p, i) => (
              <li key={p.id}>
                <span className="briefing-no">{NUMBERS[i]}</span>
                <span>
                  <span className="briefing-title">{titleOf.get(p.id)}</span> — {p.reason}
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
      {later.length > 0 && (
        <>
          <h3>미뤄도 되는 일</h3>
          <ul>
            {later.map((id) => (
              <li key={id}>{titleOf.get(id)}</li>
            ))}
          </ul>
        </>
      )}
      <p className="briefing-cheer">{briefing.cheer}</p>
      <div className="actions">
        <button type="button" onClick={onClose}>
          닫기
        </button>
      </div>
    </section>
  )
}
