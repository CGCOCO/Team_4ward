import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Shield } from 'lucide-react'
import { api, setToken } from '../api'
import Layout from '../components/Layout'

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await api.post('/api/v1/auth/login', { email, password })
      setToken(response.data.access_token)
      navigate(location.state?.from ?? '/', { replace: true })
    } catch (err) {
      setError(err.response?.data?.detail ?? '로그인에 실패했습니다.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout hideNav>
      <div className="flex-1 flex flex-col justify-center px-6 py-10">
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-blue-100 flex items-center justify-center mb-4">
            <Shield size={32} className="text-blue-600" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900">Safe-Guard AI</h1>
          <p className="text-sm text-slate-500 mt-1">계정으로 로그인하세요</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-semibold text-slate-700">이메일</span>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-blue-500"
              required
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-semibold text-slate-700">비밀번호</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm outline-none focus:border-blue-500"
              required
            />
          </label>

          {error && <p className="text-sm text-red-500">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white font-semibold py-4 rounded-2xl active:bg-blue-700 disabled:bg-slate-300"
          >
            {loading ? '로그인 중' : '로그인'}
          </button>
        </form>

        <p className="text-sm text-slate-500 text-center mt-6">
          계정이 없나요?{' '}
          <Link to="/signup" className="text-blue-600 font-semibold">
            회원가입
          </Link>
        </p>
      </div>
    </Layout>
  )
}
