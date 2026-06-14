import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { ArrowLeft, FileText, TriangleAlert, BookOpen, Lightbulb, ChevronDown, ChevronUp } from 'lucide-react'
import Layout from '../components/Layout'
import { api } from '../api'

const SEVERITY_MAP = {
  HIGH:   { label: '높음', color: 'text-orange-600 bg-orange-100' },
  MEDIUM: { label: '보통', color: 'text-amber-600 bg-amber-100' },
  LOW:    { label: '낮음', color: 'text-green-600 bg-green-100' },
}

function normalizeResult(result) {
  return result?.ai_result ?? result ?? null
}

function normalizeRisk(risk, index) {
  if (typeof risk === 'string') {
    return {
      id: index,
      title: risk,
      desc: '',
      severity: null,
    }
  }

  return {
    id: index,
    title: risk?.title ?? risk?.type ?? `위험 요소 ${index + 1}`,
    desc: risk?.description ?? risk?.desc ?? '',
    severity: risk?.severity ?? 'MEDIUM',
    recommendation: risk?.recommendation,
  }
}

function getRisks(resultData) {
  if (Array.isArray(resultData?.detected_risks)) {
    return resultData.detected_risks.map(normalizeRisk)
  }
  if (Array.isArray(resultData?.hazards)) {
    return resultData.hazards.map(normalizeRisk)
  }
  return []
}

function getAccidents(resultData) {
  if (Array.isArray(resultData?.accidents)) {
    return resultData.accidents.filter(Boolean)
  }
  return []
}

function getRecommendations(resultData, hazards) {
  const preventionItems = [
    ...(Array.isArray(resultData?.safety_measures) ? resultData.safety_measures : []),
    ...(Array.isArray(resultData?.preventions) ? resultData.preventions : []),
  ].filter(Boolean)

  if (preventionItems.length > 0) {
    return preventionItems
  }

  const riskRecommendations = hazards.map((risk) => risk.recommendation).filter(Boolean)
  if (riskRecommendations.length > 0) return riskRecommendations

  return []
}

function normalizeLaw(law, index) {
  if (typeof law === 'string') {
    const { title, subtitle } = formatLawTitle(law, '')
    return {
      id: index,
      title,
      subtitle,
      content: '',
    }
  }

  const article = law?.article ?? law?.title ?? law?.name ?? ''
  const content = law?.content ?? law?.description ?? ''
  const { title, subtitle } = formatLawTitle(article, content)

  return {
    id: law?.id ?? index,
    title: title || `관련 법규 ${index + 1}`,
    subtitle: law?.subtitle ?? subtitle,
    content,
  }
}

function formatLawTitle(article, content) {
  const articleText = String(article || '').trim()
  const contentText = String(content || '').trim()
  const articleMatch = articleText.match(/^(?:산업안전보건(?:기준에 관한 )?규칙\s*)?(제\s*\d+조)(?:\(([^)]+)\))?/)
  const contentTitleMatch = contentText.match(/^제\s*\d+조\(([^)]+)\)/)

  if (!articleMatch) {
    return {
      title: articleText,
      subtitle: contentTitleMatch?.[1] ?? '',
    }
  }

  return {
    title: `산업안전보건규칙 ${articleMatch[1].replace(/\s+/g, '')}`,
    subtitle: articleMatch[2] ?? contentTitleMatch?.[1] ?? '',
  }
}

function getLaws(resultData) {
  if (Array.isArray(resultData?.related_laws)) {
    return resultData.related_laws.map(normalizeLaw)
  }
  return []
}

export default function ResultPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { previewUrl, result, from } = location.state ?? {}
  const [storedImageUrl, setStoredImageUrl] = useState('')
  const [storedImageLoading, setStoredImageLoading] = useState(false)

  const resultData = normalizeResult(result)
  const hazards = getRisks(resultData)
  const accidents = getAccidents(resultData)
  const recommendations = getRecommendations(resultData, hazards)
  const laws = getLaws(resultData)
  const [openLaw, setOpenLaw] = useState(null)
  const [isDownloading, setIsDownloading] = useState(false)
  const shouldUseStoredImage = Boolean(result?.id && result?.image_url)
  const displayImageUrl = shouldUseStoredImage ? storedImageUrl : previewUrl
  const canDownloadReport = Boolean(result?.id)

  useEffect(() => {
    if (!result?.id || !result?.image_url) return undefined

    let objectUrl = ''
    let ignore = false

    async function loadStoredImage() {
      setStoredImageLoading(true)
      const response = await api.get(`/api/v1/analyze/${result.id}/image`, {
        responseType: 'blob',
      })
      if (ignore) return
      objectUrl = URL.createObjectURL(response.data)
      setStoredImageUrl(objectUrl)
      setStoredImageLoading(false)
    }

    loadStoredImage().catch(() => {
      if (!ignore) {
        setStoredImageUrl('')
        setStoredImageLoading(false)
      }
    })

    return () => {
      ignore = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [result?.id, result?.image_url])

  async function downloadReport() {
    if (!result?.id || isDownloading) return

    try {
      setIsDownloading(true)
      const response = await api.get(`/api/v1/analyze/${result.id}/report`, {
        responseType: 'blob',
      })
      const url = URL.createObjectURL(response.data)
      const link = document.createElement('a')
      link.href = url
      link.download = `safety-report-${result.id}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } finally {
      setIsDownloading(false)
    }
  }

  function handleBack() {
    if (from === 'history') {
      navigate('/history')
      return
    }

    navigate('/history')
  }

  if (!resultData) {
    return (
      <Layout>
        <header className="flex items-center gap-3 px-5 pt-10 pb-4 border-b border-slate-100">
          <button onClick={handleBack} className="text-slate-500">
            <ArrowLeft size={22} />
          </button>
          <h1 className="text-lg font-bold text-slate-900">분석 결과</h1>
        </header>

        <div className="flex-1 flex flex-col items-center justify-center text-center px-8">
          <div className="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mb-4">
            <FileText size={28} className="text-slate-400" />
          </div>
          <p className="text-base font-semibold text-slate-700 mb-2">표시할 분석 결과가 없습니다</p>
          <p className="text-sm text-slate-400 mb-6">새 분석을 시작하거나 이력에서 결과를 선택하세요</p>
          <div className="flex gap-2">
            <button
              onClick={() => navigate('/')}
              className="bg-blue-600 text-white font-semibold px-5 py-3 rounded-xl"
            >
              홈으로
            </button>
            <button
              onClick={() => navigate('/history')}
              className="border border-slate-300 text-slate-600 font-semibold px-5 py-3 rounded-xl"
            >
              이력 보기
            </button>
          </div>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <header className="flex items-center justify-between px-5 pt-10 pb-4 border-b border-slate-100">
        <div className="flex items-center gap-3">
          <button onClick={handleBack} className="text-slate-500">
            <ArrowLeft size={22} />
          </button>
          <h1 className="text-lg font-bold text-slate-900">분석 결과</h1>
        </div>
        <button
          onClick={downloadReport}
          disabled={!canDownloadReport || isDownloading}
          className="flex items-center gap-1.5 border border-slate-300 text-slate-600 text-sm font-medium px-3 py-1.5 rounded-lg active:bg-slate-50 disabled:opacity-40 disabled:active:bg-transparent"
        >
          <FileText size={15} />
          PDF
        </button>
      </header>

      <div className="flex flex-col px-5 py-5 gap-6">
        {/* Uploaded photo */}
        {storedImageLoading && shouldUseStoredImage ? (
          <div className="rounded-2xl bg-slate-100 aspect-[4/3] flex items-center justify-center">
            <p className="text-sm text-slate-400">마스킹된 이미지를 불러오는 중입니다</p>
          </div>
        ) : displayImageUrl && (
          <div className="rounded-2xl overflow-hidden bg-slate-100 aspect-[4/3]">
            <img src={displayImageUrl} alt="분석 사진" className="w-full h-full object-cover" />
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
                    {h.severity ? (
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full flex-shrink-0 ${sev.color}`}>
                        {sev.label}
                      </span>
                    ) : null}
                  </div>
                  {h.desc ? <p className="text-xs text-slate-500 leading-relaxed">{h.desc}</p> : null}
                </div>
              </div>
            )
          })}
        </section>

        {/* Near miss accidents */}
        {accidents.length > 0 ? (
          <section>
            <div className="flex items-center gap-2 mb-3">
              <TriangleAlert size={18} className="text-blue-600" />
              <h2 className="text-base font-bold text-slate-900">발생 가능한 아차사고</h2>
            </div>
            <div className="bg-white rounded-2xl border border-slate-200 p-4 flex flex-col gap-3">
              {accidents.map((accident, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-xs font-bold text-blue-600">{i + 1}</span>
                  </div>
                  <p className="text-sm text-slate-700 leading-relaxed">{accident}</p>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {/* Laws - accordion */}
        <section>
          <div className="flex items-center gap-2 mb-3">
            <BookOpen size={18} className="text-blue-600" />
            <h2 className="text-base font-bold text-slate-900">관련 법규</h2>
          </div>
          <div className="flex flex-col gap-2">
            {laws.map((law) => {
              const isOpen = openLaw === law.id
              return (
                <div key={law.id} className={`rounded-2xl border overflow-hidden transition-all bg-white ${isOpen ? 'border-blue-400' : 'border-slate-200'}`}>
                  <button
                    onClick={() => setOpenLaw(isOpen ? null : law.id)}
                    className="w-full flex items-center justify-between px-4 py-3.5 text-left"
                    >
                    <div>
                      <p className="text-sm font-semibold text-slate-800">{law.title}</p>
                      {law.subtitle ? (
                        <p className="text-xs text-slate-500 mt-0.5">{law.subtitle}</p>
                      ) : null}
                    </div>
                    {isOpen ? (
                      <ChevronUp size={18} className="text-slate-400 flex-shrink-0" />
                    ) : (
                      <ChevronDown size={18} className="text-slate-400 flex-shrink-0" />
                    )}
                  </button>
                  {isOpen && (
                    <div className="px-4 pb-4 border-t border-blue-100 pt-3">
                      {law.content ? (
                        <p className="text-sm text-slate-600 leading-relaxed mb-2">{law.content}</p>
                      ) : null}
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
            {recommendations.length > 0 ? (
              recommendations.map((rec, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0 mt-0.5">
                    <span className="text-xs font-bold text-green-600">{i + 1}</span>
                  </div>
                  <p className="text-sm text-slate-700 leading-relaxed">{rec}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500 leading-relaxed">예방 권고가 없습니다.</p>
            )}
          </div>
        </section>
      </div>

      {/* Bottom CTA */}
      <div className="px-5 pb-4">
        <button
          onClick={downloadReport}
          disabled={!canDownloadReport || isDownloading}
          className="w-full bg-blue-600 text-white font-semibold py-4 rounded-2xl flex items-center justify-center gap-2 text-base active:bg-blue-700 transition-colors shadow-md shadow-blue-200 disabled:opacity-45 disabled:active:bg-blue-600"
        >
          <FileText size={18} />
          {isDownloading ? 'PDF 생성 중' : 'PDF 다운로드'}
        </button>
      </div>
    </Layout>
  )
}
