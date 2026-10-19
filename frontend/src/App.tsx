import { useEffect, useState } from 'react'

type ApiStatus = 'checking' | 'connected' | 'failed'

function App() {
  const [status, setStatus] = useState<ApiStatus>('checking')

  useEffect(() => {
    fetch('/api/health')
      .then((res) => setStatus(res.ok ? 'connected' : 'failed'))
      .catch(() => setStatus('failed'))
  }, [])

  const message = {
    checking: 'API 확인 중...',
    connected: 'API 연결됨',
    failed: 'API에 연결할 수 없음',
  }[status]

  return (
    <main>
      <h1>task-flow</h1>
      <p>{message}</p>
    </main>
  )
}

export default App
