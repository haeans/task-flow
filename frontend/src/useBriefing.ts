import { useEffect, useRef, useState } from 'react'
import { ApiError, requestBriefing } from './api'
import { BRIEFING_EMPTY, briefingErrorMessage } from './errors'
import type { Briefing } from './types'

interface Message {
  text: string
  error: boolean
}

// 오늘 브리핑 요청의 상태 (R-018, D-036). 저장하지 않고, 받은 결과는 화면에만 둔다.
export function useBriefing(onUnauthorized: () => void) {
  const [loading, setLoading] = useState(false)
  const [briefing, setBriefing] = useState<Briefing | null>(null)
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
    setBriefing(null)
    try {
      const b = await requestBriefing()
      if (!mounted.current) return
      // 완료가 아닌 할 일이 0개이면 서버가 빈 목록으로 200을 준다. 서버 문구에 기대지 않는다.
      if (b.top3.length === 0 && b.later.length === 0) {
        setMessage({ text: BRIEFING_EMPTY, error: false })
      } else {
        setBriefing(b)
      }
    } catch (e) {
      if (!mounted.current) return
      if (e instanceof ApiError && e.status === 401) {
        onUnauthorized()
        return
      }
      setMessage({ text: briefingErrorMessage(e), error: true })
    } finally {
      if (mounted.current) setLoading(false)
    }
  }

  function close() {
    setBriefing(null)
    setMessage(null)
  }

  return { loading, briefing, message, make, close }
}
