import { useState } from 'react'
import { Shield, CheckCircle, Upload } from 'lucide-react'
import Layout from '../components/Layout'

// TODO: API에서 분석 사례 목록 fetch
const MOCK_CASES = [
  { id: 1, title: '3공장 B구역 점검', date: '2025-05-15', hazardCount: 4, saved: true },
  { id: 2, title: '사무동 2층 안전 점검', date: '2025-05-12', hazardCount: 2, saved: false },
  { id: 3, title: '물류 센터 주간 점검', date: '2025-05-10', hazardCount: 6, saved: true },
]

export default function AdminPage() {
  const [cases, setCases] = useState(MOCK_CASES)

  const handleSave = (id) => {
    // TODO: POST /api/admin/cases/:id/save → ChromaDB 저장
    setCases((prev) => prev.map((c) => (c.id === id ? { ...c, saved: true } : c)))
  }

  return (
    <Layout>
      <header className="px-5 pt-10 pb-4 border-b border-slate-100">
        <p className="text-xs text-blue-600 font-semibold mb-1">관리자</p>
        <h1 className="text-xl font-bold text-slate-900">우수 사례 관리</h1>
        <p className="text-sm text-slate-500 mt-1">RAG 학습에 활용할 우수 진단 사례를 저장합니다</p>
      </header>

      <div className="px-5 py-4 flex flex-col gap-4">
        {/* Stats */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-blue-50 rounded-2xl p-4 border border-blue-100">
            <p className="text-2xl font-bold text-blue-600">
              {cases.filter((c) => c.saved).length}
            </p>
            <p className="text-xs text-blue-400 mt-0.5">저장된 사례</p>
          </div>
          <div className="bg-slate-50 rounded-2xl p-4 border border-slate-100">
            <p className="text-2xl font-bold text-slate-700">{cases.length}</p>
            <p className="text-xs text-slate-400 mt-0.5">전체 진단</p>
          </div>
        </div>

        {/* PDF upload for custom regulations */}
        <div className="bg-white rounded-2xl border border-dashed border-blue-300 p-4 flex flex-col items-center gap-2">
          <div className="w-10 h-10 rounded-xl bg-blue-50 flex items-center justify-center">
            <Upload size={20} className="text-blue-500" />
          </div>
          <p className="text-sm font-semibold text-slate-700">사내 규정 PDF 업로드</p>
          <p className="text-xs text-slate-400 text-center">업로드한 PDF를 기반으로 커스텀 RAG를 구성합니다</p>
          {/* TODO: PDF 업로드 → POST /api/admin/regulations */}
          <button className="mt-1 bg-blue-600 text-white text-sm font-semibold px-5 py-2 rounded-xl active:bg-blue-700">
            파일 선택
          </button>
        </div>

        {/* Case list */}
        <div className="flex flex-col gap-3">
          <p className="text-sm font-semibold text-slate-700">진단 사례 목록</p>
          {cases.map((c) => (
            <div key={c.id} className="bg-white rounded-2xl border border-slate-200 p-4">
              <div className="flex items-start justify-between mb-1">
                <p className="text-sm font-semibold text-slate-800">{c.title}</p>
                {c.saved && (
                  <div className="flex items-center gap-1 text-xs text-green-600 font-semibold flex-shrink-0 ml-2">
                    <CheckCircle size={13} />
                    저장됨
                  </div>
                )}
              </div>
              <p className="text-xs text-slate-400 mb-3">
                {c.date} · 위험 요소 {c.hazardCount}건
              </p>
              {!c.saved && (
                <button
                  onClick={() => handleSave(c.id)}
                  className="w-full bg-blue-50 text-blue-600 font-semibold text-sm py-2.5 rounded-xl border border-blue-200 active:bg-blue-100 transition-colors flex items-center justify-center gap-1.5"
                >
                  <Shield size={15} />
                  ChromaDB에 우수 사례 저장
                </button>
              )}
            </div>
          ))}
        </div>
      </div>
    </Layout>
  )
}
