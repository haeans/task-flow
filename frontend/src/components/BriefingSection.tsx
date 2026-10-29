import { useBriefing } from '../useBriefing'
import type { Task } from '../types'
import BriefingCard from './BriefingCard'

interface Props {
  tasks: Task[]
  // 로그인이 끝났을 때 (R-010)
  onUnauthorized: () => void
}

// 보드 바로 위의 [오늘 브리핑] 버튼과 결과 카드 (R-018, D-036).
export default function BriefingSection({ tasks, onUnauthorized }: Props) {
  const { loading, briefing, message, make, close } = useBriefing(onUnauthorized)

  return (
    <div className="briefing">
      {/* type="button": 눌러도 등록·저장(submit)이 실행되지 않는다. */}
      <button type="button" onClick={make} disabled={loading}>
        {loading ? '만드는 중…' : '오늘 브리핑'}
      </button>
      {message && (
        <p role={message.error ? 'alert' : 'status'} className={message.error ? 'error' : 'info'}>
          {message.text}
        </p>
      )}
      {briefing && <BriefingCard briefing={briefing} tasks={tasks} onClose={close} />}
    </div>
  )
}
