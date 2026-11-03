import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { login } from '../api'
import { authErrorMessage } from '../errors'
import { validateLoginInput } from '../validate'

// 로그인이 끝났다는 알림이나 가입 직후 안내는 이동하면서 state로 받는다.
export interface AuthLocationState {
  notice?: string
  info?: string
}

export default function LoginPage() {
  const navigate = useNavigate()
  const state = (useLocation().state ?? {}) as AuthLocationState
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    const invalid = validateLoginInput(username, password)
    if (invalid) {
      setError(invalid)
      return
    }
    setBusy(true)
    setError(null)
    try {
      await login(username, password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(authErrorMessage(err, 'login'))
      setBusy(false)
    }
  }

  return (
    <main>
      <header className="top">
        <h1>task-flow</h1>
      </header>
      <form className="auth" onSubmit={submit}>
        <h2>로그인</h2>
        {state.info ? (
          <p role="status" className="info">
            {state.info}
          </p>
        ) : (
          state.notice && <p className="info">{state.notice}</p>
        )}
        <label>
          아이디
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            autoFocus
          />
        </label>
        <label>
          비밀번호
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />
        </label>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <div className="actions">
          <button type="button" onClick={() => navigate('/signup')} disabled={busy}>
            가입하기
          </button>
          <button type="submit" disabled={busy}>
            {busy ? '처리 중...' : '로그인'}
          </button>
        </div>
      </form>
    </main>
  )
}
