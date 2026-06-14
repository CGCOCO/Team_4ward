import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BarChart3, FileText, LogOut, Mail, Upload, User } from 'lucide-react'
import Layout from '../components/Layout'
import { api, clearToken } from '../api'

export default function AdminPage() {
  const navigate = useNavigate()
  const [history, setHistory] = useState([])
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [regulationFile, setRegulationFile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let ignore = false

    async function loadMyPage() {
      try {
        const [meResponse, historyResponse] = await Promise.all([
          api.get('/api/v1/auth/me'),
          api.get('/api/v1/analyze/history'),
        ])
        if (ignore) return

        setName(meResponse.data.name ?? '')
        setEmail(meResponse.data.email ?? '')
        setHistory(historyResponse.data)
      } catch (err) {
        if (err.response?.status === 401) {
          clearToken()
          navigate('/login', { replace: true })
          return
        }
        if (!ignore) setError('마이페이지 정보를 불러오지 못했습니다.')
      } finally {
        if (!ignore) setLoading(false)
      }
    }

    loadMyPage()

    return () => {
      ignore = true
    }
  }, [navigate])

  function handleLogout() {
    clearToken()
    navigate('/login', { replace: true })
  }

  return (
    <Layout>
      <header className="px-5 pt-10 pb-4 border-b border-slate-100">
        <p className="text-xs text-blue-600 font-semibold mb-1">마이페이지</p>
        <h1 className="text-xl font-bold text-slate-900">계정 관리</h1>
        <p className="text-sm text-slate-500 mt-1">계정 정보와 회사 내규 자료를 관리합니다</p>
      </header>

      <div className="px-5 py-4 flex flex-col gap-4">
        {loading ? (
          <div className="bg-white rounded-2xl border border-slate-200 p-5">
            <p className="text-sm text-slate-400">마이페이지 정보를 불러오는 중입니다</p>
          </div>
        ) : error ? (
          <div className="bg-white rounded-2xl border border-red-100 p-5">
            <p className="text-sm font-semibold text-red-500">{error}</p>
          </div>
        ) : (
          <>
            <section className="bg-white rounded-2xl border border-slate-200 p-4">
              <div className="flex items-center gap-2 mb-3">
                <BarChart3 size={18} className="text-blue-600" />
                <h2 className="text-base font-bold text-slate-900">사용 현황</h2>
              </div>
              <div className="bg-blue-50 rounded-2xl p-4 border border-blue-100">
                <p className="text-3xl font-bold text-blue-600">{history.length}</p>
                <p className="text-sm font-semibold text-blue-500 mt-1">총 분석 건수</p>
                <p className="text-xs text-blue-400 mt-1">현재 계정으로 생성한 진단 이력 기준입니다</p>
              </div>
            </section>

            <section className="bg-white rounded-2xl border border-slate-200 p-4">
              <div className="flex items-center gap-2 mb-4">
                <User size={18} className="text-blue-600" />
                <h2 className="text-base font-bold text-slate-900">내 정보</h2>
              </div>
              <div className="flex flex-col gap-3">
                <div className="rounded-xl bg-slate-50 border border-slate-100 px-4 py-3">
                  <p className="text-xs font-semibold text-slate-400 mb-1">이름</p>
                  <p className="text-sm font-semibold text-slate-800">{name || '이름 없음'}</p>
                </div>
                <div className="rounded-xl bg-slate-50 border border-slate-100 px-4 py-3">
                  <div className="flex items-center gap-2 mb-1">
                    <Mail size={14} className="text-slate-400" />
                    <p className="text-xs font-semibold text-slate-400">이메일</p>
                  </div>
                  <p className="text-sm font-semibold text-slate-800">{email}</p>
                </div>
              </div>
            </section>

            <section className="bg-white rounded-2xl border border-dashed border-blue-300 p-4">
              <div className="flex items-center gap-2 mb-2">
                <Upload size={18} className="text-blue-600" />
                <h2 className="text-base font-bold text-slate-900">회사 내규 PDF</h2>
              </div>
              <p className="text-sm text-slate-500 mb-3">
                회사 내부 안전 규정을 업로드해 전용 RAG 자료로 활용합니다.
              </p>
              <label className="flex items-center justify-center gap-2 border border-slate-200 rounded-xl px-4 py-3 text-sm font-semibold text-slate-600 active:bg-slate-50">
                <FileText size={16} />
                <span>{regulationFile ? regulationFile.name : 'PDF 파일 선택'}</span>
                <input
                  type="file"
                  accept="application/pdf"
                  className="hidden"
                  onChange={(e) => setRegulationFile(e.target.files?.[0] ?? null)}
                />
              </label>
              <button
                type="button"
                disabled
                className="w-full mt-3 bg-slate-200 text-slate-500 font-semibold py-3 rounded-xl"
              >
                RAG 업로드 연동 예정
              </button>
            </section>

            <button
              onClick={handleLogout}
              className="w-full flex items-center justify-center gap-2 border border-slate-200 text-slate-600 font-semibold py-3 rounded-xl active:bg-slate-50"
            >
              <LogOut size={17} />
              로그아웃
            </button>
          </>
        )}
      </div>
    </Layout>
  )
}
