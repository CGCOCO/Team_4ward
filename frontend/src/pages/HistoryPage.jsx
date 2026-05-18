import { useNavigate } from 'react-router-dom'
import { ArrowLeft, MapPin, ChevronRight } from 'lucide-react'
import Layout from '../components/Layout'

// TODO: API에서 사용자 진단 이력 fetch
const MOCK_HISTORY = [
  { id: 1, title: '3공장 B구역 점검', date: '2025-05-15', location: '3공장 B구역', high: 2, med: 2, low: 0 },
  { id: 2, title: '사무동 2층 안전 점검', date: '2025-05-12', location: '사무동 2층', high: 0, med: 2, low: 1 },
  { id: 3, title: '물류 센터 주간 점검', date: '2025-05-10', location: '물류 센터', high: 3, med: 3, low: 0 },
]

const severityBadges = [
  { key: 'high', label: '고위험', style: 'bg-red-100 text-red-600' },
  { key: 'med', label: '중위험', style: 'bg-amber-100 text-amber-600' },
  { key: 'low', label: '저위험', style: 'bg-green-100 text-green-600' },
]

export default function HistoryPage() {
  const navigate = useNavigate()

  return (
    <Layout>
      <header className="px-5 pt-10 pb-4 border-b border-slate-100">
        <h1 className="text-xl font-bold text-slate-900">진단 이력</h1>
        <p className="text-sm text-slate-500 mt-1">최근 안전 진단 결과를 확인합니다</p>
      </header>

      {MOCK_HISTORY.length === 0 ? (
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
          {MOCK_HISTORY.map((h) => (
            <button
              key={h.id}
              onClick={() => navigate('/result')}
              className="text-left bg-white rounded-2xl border border-slate-200 p-4 active:bg-slate-50 transition-colors w-full"
            >
              <div className="flex items-start justify-between mb-1">
                <p className="text-sm font-semibold text-slate-800">{h.title}</p>
                <ChevronRight size={16} className="text-slate-300 flex-shrink-0 mt-0.5" />
              </div>
              <div className="flex items-center gap-1 text-xs text-slate-400 mb-3">
                <MapPin size={11} />
                <span>{h.location}</span>
                <span className="mx-1">·</span>
                <span>{h.date}</span>
              </div>
              <div className="flex gap-2 flex-wrap">
                {severityBadges.map(({ key, label, style }) =>
                  h[key] > 0 ? (
                    <span key={key} className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${style}`}>
                      {label} {h[key]}건
                    </span>
                  ) : null
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </Layout>
  )
}
