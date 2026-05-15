import { useNavigate } from 'react-router-dom'
import { ArrowLeft, Share2, Shield, Calendar, Clock, Download, Zap, Flame, TriangleAlert } from 'lucide-react'
import Layout from '../components/Layout'

// TODO: useLocation()으로 실제 보고서 데이터 받아오기
const MOCK_REPORT = {
  date: '2026년 5월 15일',
  time: '오후 07:22',
  totalHazards: 3,
  urgent: 2,
  riskScore: 78,
  items: [
    {
      no: 1,
      icon: Zap,
      iconColor: 'text-blue-500',
      iconBg: 'bg-blue-100',
      title: '전선 방치로 인한 넘어짐 위험',
      desc: '바닥에 방치된 전선이 보행자의 통행을 방해하고 있습니다.',
      freq: '자주',
      freqColor: 'text-orange-600 bg-orange-100',
      severity: '높음',
      severityColor: 'text-orange-600 bg-orange-100',
      measure: '전선 정리 및 케이블 트레이 사용',
      law: '산업안전보건규칙 제32조',
    },
    {
      no: 2,
      icon: Flame,
      iconColor: 'text-red-500',
      iconBg: 'bg-red-100',
      title: '노후 멀티탭으로 감전 위험',
      desc: '손상된 멀티탭에서 과열 및 합선 위험이 있습니다.',
      freq: '매우 자주',
      freqColor: 'text-red-600 bg-red-100',
      severity: '심각',
      severityColor: 'text-red-600 bg-red-100',
      measure: '멀티탭 교체 권장',
      law: '산업안전보건규칙 제311조',
    },
    {
      no: 3,
      icon: TriangleAlert,
      iconColor: 'text-orange-500',
      iconBg: 'bg-orange-100',
      title: '미끄러운 바닥면',
      desc: '바닥에 물기가 있어 미끄러짐 위험이 있습니다.',
      freq: '가끔',
      freqColor: 'text-amber-600 bg-amber-100',
      severity: '보통',
      severityColor: 'text-amber-600 bg-amber-100',
      measure: '미끄럼 방지 매트 설치 또는 즉시 청소',
      law: '산업안전보건규칙 제24조',
    },
  ],
}

export default function ReportPage() {
  const navigate = useNavigate()

  return (
    <Layout>
      <header className="flex items-center justify-between px-5 pt-10 pb-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="text-slate-500">
            <ArrowLeft size={22} />
          </button>
          <h1 className="text-lg font-bold text-slate-900">위험성 평가 리포트</h1>
        </div>
        <button className="text-slate-500 active:text-slate-700">
          <Share2 size={20} />
        </button>
      </header>

      <div className="flex flex-col px-5 py-5 gap-5 pb-6">
        {/* Blue header card */}
        <div className="bg-blue-600 rounded-2xl p-5 text-white">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
              <Shield size={22} className="text-white" />
            </div>
            <div>
              <p className="text-base font-bold">AI 안전 점검 리포트</p>
              <p className="text-xs text-blue-200">자동 생성된 위험성 평가 보고서</p>
            </div>
          </div>
          <div className="flex items-center gap-5 text-sm text-blue-100">
            <div className="flex items-center gap-1.5">
              <Calendar size={14} />
              <span>{MOCK_REPORT.date}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Clock size={14} />
              <span>{MOCK_REPORT.time}</span>
            </div>
          </div>
        </div>

        {/* Summary */}
        <div className="bg-white rounded-2xl border border-slate-200 p-4">
          <p className="text-sm font-semibold text-slate-700 mb-3">요약</p>
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-slate-50 rounded-xl p-3 text-center">
              <p className="text-2xl font-bold text-blue-600">{MOCK_REPORT.totalHazards}</p>
              <p className="text-xs text-slate-500 mt-0.5">발견된 위험</p>
            </div>
            <div className="bg-slate-50 rounded-xl p-3 text-center">
              <p className="text-2xl font-bold text-red-500">{MOCK_REPORT.urgent}</p>
              <p className="text-xs text-slate-500 mt-0.5">긴급 조치</p>
            </div>
            <div className="bg-slate-50 rounded-xl p-3 text-center">
              <p className="text-2xl font-bold text-orange-500">{MOCK_REPORT.riskScore}점</p>
              <p className="text-xs text-slate-500 mt-0.5">위험 점수</p>
            </div>
          </div>
        </div>

        {/* Hazard detail items */}
        <section>
          <p className="text-sm font-semibold text-slate-700 mb-3">위험 요소 상세</p>
          <div className="flex flex-col gap-3">
            {MOCK_REPORT.items.map((item) => {
              const Icon = item.icon
              return (
                <div key={item.no} className="bg-white rounded-2xl border border-slate-200 p-4 flex flex-col gap-3">
                  {/* Title row */}
                  <div className="flex items-start gap-3">
                    <div className={`w-10 h-10 rounded-xl ${item.iconBg} flex items-center justify-center flex-shrink-0`}>
                      <Icon size={20} className={item.iconColor} />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-slate-800">
                        {item.no}. {item.title}
                      </p>
                      <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{item.desc}</p>
                    </div>
                  </div>

                  {/* Freq / Severity grid */}
                  <div className="grid grid-cols-2 gap-2">
                    <div className="bg-slate-50 rounded-xl p-3">
                      <p className="text-xs text-slate-500 mb-1.5">빈도 (추정)</p>
                      <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${item.freqColor}`}>
                        {item.freq}
                      </span>
                    </div>
                    <div className="bg-slate-50 rounded-xl p-3">
                      <p className="text-xs text-slate-500 mb-1.5">심각도</p>
                      <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${item.severityColor}`}>
                        {item.severity}
                      </span>
                    </div>
                  </div>

                  {/* Measure */}
                  <div className="bg-green-50 rounded-xl px-4 py-3 border border-green-100">
                    <p className="text-xs text-green-700 font-semibold mb-1">개선 조치</p>
                    <p className="text-sm text-green-800">{item.measure}</p>
                  </div>

                  <p className="text-xs text-slate-400">
                    관련 법규: <span className="text-slate-600 font-medium">{item.law}</span>
                  </p>
                </div>
              )
            })}
          </div>
        </section>

        {/* Download */}
        <button className="w-full bg-blue-600 text-white font-semibold py-4 rounded-2xl flex items-center justify-center gap-2 text-base active:bg-blue-700 transition-colors shadow-md shadow-blue-200">
          <Download size={18} />
          PDF 다운로드
        </button>
      </div>
    </Layout>
  )
}
