import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { ArrowLeft, FileText, TriangleAlert, BookOpen, Lightbulb, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import Layout from '../components/Layout'

const SEVERITY_MAP = {
  HIGH:   { label: '높음', color: 'text-orange-600 bg-orange-100' },
  MEDIUM: { label: '보통', color: 'text-amber-600 bg-amber-100' },
  LOW:    { label: '낮음', color: 'text-green-600 bg-green-100' },
}

const FALLBACK_HAZARDS = [
  { id: 1, title: '사다리 고정 장치 미설치', desc: '사다리가 벽면에 고정되지 않아 전도 위험이 있습니다.', severity: 'HIGH' },
  { id: 2, title: '미끄러운 바닥면', desc: '바닥에 물기가 있어 미끄러짐 위험이 있습니다.', severity: 'MEDIUM' },
]

const FALLBACK_RECOMMENDATIONS = [
  '전선 정리 및 케이블 트레이 사용',
  '미끄럼 방지 매트 설치 또는 즉시 청소',
  '정기적인 안전 점검 일정 수립',
]

const MOCK_LAWS = [
  { id: 1, title: '산업안전보건규칙 제32조', subtitle: '통로', content: '통로의 주요 부분에는 통로임을 표시하고, 항상 안전한 상태를 유지하여야 합니다.' },
  { id: 2, title: '산업안전보건규칙 제311조', subtitle: '전기설비의 점검', content: '전기기계·기구는 정기적으로 점검하고 이상이 있을 경우 즉시 수리해야 합니다.' },
  { id: 3, title: '산업안전보건규칙 제24조', subtitle: '작업장 바닥', content: '작업장 바닥은 안전하고 청결한 상태를 유지하여야 합니다.' },
]

export default function ResultPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { previewUrl, result } = location.state ?? {}

  const rawRisks = result?.detected_risks ?? FALLBACK_HAZARDS
  const hazards = rawRisks.map((r, i) => ({
    id: i,
    title: r.title ?? r.type ?? `위험 요소 ${i + 1}`,
    desc: r.description ?? r.desc ?? '',
    severity: r.severity ?? 'MEDIUM',
  }))
  const recommendations = result
    ? rawRisks.map((r) => r.recommendation).filter(Boolean)
    : FALLBACK_RECOMMENDATIONS
  const [openLaw, setOpenLaw] = useState(null)

  return (
    <Layout>
      <header className="flex items-center justify-between px-5 pt-10 pb-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="text-slate-500">
            <ArrowLeft size={22} />
          </button>
          <h1 className="text-lg font-bold text-slate-900">분석 결과</h1>
        </div>
        <button
          onClick={() => navigate('/report')}
          className="flex items-center gap-1.5 border border-slate-300 text-slate-600 text-sm font-medium px-3 py-1.5 rounded-lg active:bg-slate-50"
        >
          <FileText size={15} />
          리포트
        </button>
      </header>

      <div className="flex flex-col px-5 py-5 gap-6">
        {/* Uploaded photo */}
        {previewUrl && (
          <div className="rounded-2xl overflow-hidden bg-slate-100 aspect-[4/3]">
            <img src={previewUrl} alt="분석 사진" className="w-full h-full object-cover" />
          </div>
        )}

        {/* Hazard list */}
        <section className="flex flex-col gap-3">
          {hazards.map((h) => {
            const sev = SEVERITY_MAP[h.severity] ?? SEVERITY_MAP.MEDIUM
            return (
              <div key={h.id} className="bg-white rounded-2xl border border-slate-200 p-4 flex items-start gap-3">
                <div className="w-10 h-10 rounded-xl bg-orange-100 flex items-center justify-center flex-shrink-0">
                  <TriangleAlert size={20} className="text-orange-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <p className="text-sm font-semibold text-slate-800">{h.title}</p>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full flex-shrink-0 ${sev.color}`}>
                      {sev.label}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 leading-relaxed">{h.desc}</p>
                </div>
              </div>
            )
          })}
        </section>

        {/* Laws - accordion */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <BookOpen size={18} className="text-blue-600" />
            <h2 className="text-base font-bold text-slate-900">관련 법규</h2>
          </div>
          <div className="flex flex-col gap-2">
            {MOCK_LAWS.map((law) => {
              const isOpen = openLaw === law.id
              return (
                <div key={law.id} className={`rounded-2xl border overflow-hidden transition-all bg-white ${isOpen ? 'border-blue-400' : 'border-slate-200'}`}>
                  <button
                    onClick={() => setOpenLaw(isOpen ? null : law.id)}
                    className="w-full flex items-center justify-between px-4 py-3.5 text-left"
                  >
                    <div>
                      <p className="text-sm font-semibold text-slate-800">{law.title}</p>
                      <p className="text-xs text-slate-500 mt-0.5">{law.subtitle}</p>
                    </div>
                    {isOpen ? (
                      <ChevronUp size={18} className="text-slate-400 flex-shrink-0" />
                    ) : (
                      <ChevronDown size={18} className="text-slate-400 flex-shrink-0" />
                    )}
                  </button>
                  {isOpen && (
                    <div className="px-4 pb-4 border-t border-blue-100 pt-3">
                      <p className="text-sm text-slate-600 leading-relaxed mb-2">{law.content}</p>
                      <button className="flex items-center gap-1 text-blue-600 text-sm font-medium">
                        자세히 보기 <ExternalLink size={13} />
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </section>

        {/* Recommendations */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb size={18} className="text-amber-500" />
            <h2 className="text-base font-bold text-slate-900">AI 예방 권고</h2>
          </div>
          <div className="bg-white rounded-2xl border border-slate-200 p-4 flex flex-col gap-3">
            {recommendations.map((rec, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <span className="text-xs font-bold text-green-600">{i + 1}</span>
                </div>
                <p className="text-sm text-slate-700 leading-relaxed">{rec}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      {/* Bottom CTA */}
      <div className="px-5 pb-4">
        <button
          onClick={() => navigate('/report')}
          className="w-full bg-blue-600 text-white font-semibold py-4 rounded-2xl flex items-center justify-center gap-2 text-base active:bg-blue-700 transition-colors shadow-md shadow-blue-200"
        >
          <FileText size={18} />
          상세 리포트 보기
        </button>
      </div>
    </Layout>
  )
}
