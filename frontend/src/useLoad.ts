import { useCallback, useEffect, useState } from 'react'
import { ApiError } from './api'

// 불러오는 중, 성공, 실패 (B-3, B-4). 로그인하지 않음(B-5)은 401이므로 상태로 두지 않고 onUnauthorized로 넘긴다.
export type LoadState = 'loading' | 'ready' | 'failed'

// fetcher와 onUnauthorized는 바뀌지 않는 함수를 넘긴다.
export function useLoad<T>(fetcher: () => Promise<T>, initial: T, onUnauthorized: () => void) {
  const [state, setState] = useState<LoadState>('loading')
  const [data, setData] = useState<T>(initial)
  const [error, setError] = useState<unknown>(null)

  const load = useCallback(() => {
    fetcher()
      .then((value) => {
        setData(value)
        setState('ready')
      })
      .catch((e) => {
        // 새로고침했을 때 로그인 상태는 목록 요청의 401/200으로 안다.
        if (e instanceof ApiError && e.status === 401) {
          onUnauthorized()
          return
        }
        setError(e)
        setState('failed')
      })
  }, [fetcher, onUnauthorized])

  useEffect(load, [load])

  const reload = useCallback(() => {
    setState('loading')
    load()
  }, [load])

  return { state, data, setData, error, reload }
}
