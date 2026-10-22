import { useState } from 'react'
import { login, signup } from '../api'
import { authErrorMessage } from '../errors'
import { validateLoginInput, validateSignupInput } from '../validate'

interface Props {
  // 로그인이 끝났다는 알림 등, 화면 위에 보여 줄 안내.
  notice?: string | null
  onLoggedIn: () => void
}

// 가입과 로그인을 한 화면에서 전환한다 (A-5). 가입한 뒤에는 자동으로 로그인하지 않고
// 로그인 화면으로 돌아온다 (D-026).
export default function AuthScreen({ notice, onLoggedIn }: Props) {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  function switchMode(next: 'login' | 'signup') {
    setMode(next)
    setError(null)
    setInfo(null)
    setPassword('')
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    const invalid =
      mode === 'signup'
        ? validateSignupInput(username, password)
        : validateLoginInput(username, password)
    if (invalid) {
      setError(invalid)
      return
    }
    setBusy(true)
    setError(null)
    setInfo(null)
    try {
      if (mode === 'signup') {
        await signup(username, password)
        setMode('login')
        setPassword('')
        setInfo('가입했습니다. 로그인하세요.')
      } else {
        await login(username, password)
        onLoggedIn()
        return
      }
    } catch (err) {
      setError(authErrorMessage(err, mode))
    }
    setBusy(false)
  }

  return (
    <form className="auth" onSubmit={submit}>
      <h2>{mode === 'login' ? '로그인' : '가입'}</h2>
      {notice && !info && <p className="info">{notice}</p>}
      {info && (
        <p role="status" className="info">
          {info}
        </p>
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
          autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
        />
      </label>
      {mode === 'signup' && (
        <p className="hint">아이디는 4~20자의 영문과 숫자, 비밀번호는 8~100자입니다.</p>
      )}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="actions">
        <button
          type="button"
          onClick={() => switchMode(mode === 'login' ? 'signup' : 'login')}
          disabled={busy}
        >
          {mode === 'login' ? '가입하기' : '로그인으로'}
        </button>
        <button type="submit" disabled={busy}>
          {busy ? '처리 중...' : mode === 'login' ? '로그인' : '가입'}
        </button>
      </div>
    </form>
  )
}
