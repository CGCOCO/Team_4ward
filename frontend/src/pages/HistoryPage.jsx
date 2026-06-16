import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertCircle, CalendarDays, ChevronRight, FileText, Loader2 } from 'lucide-react'
import Layout from '../components/Layout'
import { api, clearToken } from '../api'

const severityBadges = [
  { key: 'high', label: '고위험', style: 'bg-red-100 text-red-600' },
  { key: 'med', label: '중위험', style: 'bg-amber-100 text-amber-600' },
  { key: 'low', label: '저위험', style: 'bg-green-100 text-green-600' },
]

const agentCountBadges = [
  { key: 'hazards', label: '위험요소', style: 'bg-orange-100 text-orange-600' },
  { key: 'accidents', label: '아차사고', style: 'bg-blue-100 text-blue-600' },
  { key: 'preventions', label: '예방대책', style: 'bg-green-100 text-green-600' },
]

function formatDate(value) {
  if (!value) return '-'
  return value.split(' ')[0]
}

function getRisks(aiResult) {
  if (Array.isArray(aiResult?.detected_risks)) return aiResult.detected_risks
  return []
}

function isAgentResult(aiResult) {
  return Array.isArray(aiResult?.hazards)
}

function countSeverities(risks) {
  return risks.reduce(
    (acc, risk) => {
      const severity = risk?.severity ?? 'MEDIUM'
      if (severity === 'HIGH') acc.high += 1
      else if (severity === 'LOW') acc.low += 1
      else acc.med += 1
      return acc
    },
    { high: 0, med: 0, low: 0 },
  )
}

function getHistoryTitle(item) {
  const aiResult = item.ai_result ?? {}
  const firstRisk = getRisks(aiResult)[0]
  const firstHazard = aiResult.hazards?.[0]
  return aiResult.summary ?? firstRisk?.title ?? firstHazard ?? `분석 결과 #${item.id}`
}

function getAgentCounts(aiResult) {
  return {
    hazards: aiResult?.hazards?.length ?? 0,
    accidents: aiResult?.accidents?.length ?? 0,
    preventions: aiResult?.preventions?.length ?? 0,
  }
}

export default function HistoryPage() {
  const navigate = useNavigate()
  const [history, setHistory] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    let ignore = false

    async function loadHistory() {
      try {
        const response = await api.get('/api/v1/analyze/history')
        if (!ignore) {
          setHistory(response.data)
          setError('')
        }
      } catch (err) {
        if (err.response?.status === 401) {
          clearToken()
          navigate('/login', { replace: true })
          return
        }
        if (!ignore) setError('진단 이력을 불러오지 못했습니다.')
      } finally {
        if (!ignore) setIsLoading(false)
      }
    }

    loadHistory()

    return () => {
      ignore = true
    }
  }, [navigate])

  return (
    <Layout>
      <header className="px-5 pt-10 pb-4 border-b border-slate-100">
        <h1 className="text-xl font-bold text-slate-900">진단 이력</h1>
        <p className="text-sm text-slate-500 mt-1">최근 안전 진단 결과를 확인합니다</p>
      </header>

      {isLoading ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
          <Loader2 size={28} className="text-blue-500 animate-spin mb-3" />
          <p className="text-sm font-medium text-slate-500">진단 이력을 불러오는 중입니다</p>
        </div>
      ) : error ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
          <div className="w-16 h-16 rounded-2xl bg-red-50 flex items-center justify-center mb-4">
            <AlertCircle size={28} className="text-red-400" />
          </div>
          <p className="text-base font-semibold text-slate-700 mb-2">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="bg-blue-600 text-white font-semibold px-6 py-3 rounded-xl"
          >
            다시 시도
          </button>
        </div>
      ) : history.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
          <div className="w-16 h-16 rounded-2xl bg-blue-50 flex items-center justify-center mb-4">
            <FileText size={28} className="text-blue-400" />
          </div>
          <p className="text-base font-semibold text-slate-700 mb-2">진단 이력이 없습니다</p>
          <p className="text-sm text-slate-400 mb-6">첫 번째 안전 진단을 시작해보세요</p>
          <button
            onClick={() => navigate('/')}
            className="bg-blue-600 text-white font-semibold px-6 py-3 rounded-xl"
          >
            진단 시작하기
          </button>
        </div>
      ) : (
        <div className="px-5 py-4 flex flex-col gap-3">
          {history.map((item) => {
            const risks = getRisks(item.ai_result)
            const counts = countSeverities(risks)
            const agentCounts = getAgentCounts(item.ai_result)
            return (
            <button
              key={item.id}
              onClick={() => navigate('/result', { state: { result: item, from: 'history' } })}
              className="text-left bg-white rounded-2xl border border-slate-200 p-4 active:bg-slate-50 transition-colors w-full"
            >
              <div className="flex items-start justify-between mb-1">
                <p className="text-sm font-semibold text-slate-800">{getHistoryTitle(item)}</p>
                <ChevronRight size={16} className="text-slate-300 flex-shrink-0 mt-0.5" />
              </div>
              <div className="flex items-center gap-1 text-xs text-slate-400 mb-3">
                <CalendarDays size={11} />
                <span>{formatDate(item.created_at)}</span>
              </div>
              <div className="flex gap-2 flex-wrap">
                {isAgentResult(item.ai_result)
                  ? agentCountBadges.map(({ key, label, style }) =>
                    agentCounts[key] > 0 ? (
                      <span key={key} className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${style}`}>
                        {label} {agentCounts[key]}건
                      </span>
                    ) : null
                  )
                  : severityBadges.map(({ key, label, style }) =>
                    counts[key] > 0 ? (
                    <span key={key} className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${style}`}>
                      {label} {counts[key]}건
                    </span>
                    ) : null
                  )}
              </div>
            </button>
            )
          })}
        </div>
      )}
    </Layout>
  )
}
