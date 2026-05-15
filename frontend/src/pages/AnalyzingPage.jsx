import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import Layout from '../components/Layout'

const steps = [
  '이미지 전처리 및 개인정보 마스킹',
  '위험 요소 감지 중',
  '산업안전보건규칙 대조 중',
  '예방 조치 생성 중',
  '위험성 평가 보고서 작성 중',
]

export default function AnalyzingPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { previewUrl } = location.state ?? {}
  const [currentStep, setCurrentStep] = useState(0)

  useEffect(() => {
    const timers = steps.map((_, i) =>
      setTimeout(() => setCurrentStep(i), i * 1200)
    )
    // TODO: 실제 API 응답 받으면 navigate('/result', { state: { result, previewUrl } })
    const done = setTimeout(() => navigate('/result', { state: { previewUrl } }), steps.length * 1200 + 800)
    return () => {
      timers.forEach(clearTimeout)
      clearTimeout(done)
    }
  }, [navigate])

  return (
    <Layout hideNav>
      <div className="flex-1 flex flex-col items-center justify-center px-8 text-center">
        {/* Spinner */}
        <div className="relative w-24 h-24 mb-8">
          <div className="absolute inset-0 rounded-full border-4 border-slate-100" />
          <div className="absolute inset-0 rounded-full border-4 border-t-orange-500 animate-spin" />
          <span className="absolute inset-0 flex items-center justify-center text-3xl">🦺</span>
        </div>

        <h2 className="text-xl font-bold text-slate-900 mb-2">AI가 현장을 분석 중입니다</h2>
        <p className="text-sm text-slate-500 mb-10">잠시만 기다려 주세요</p>

        {/* Steps progress */}
        <div className="w-full max-w-xs flex flex-col gap-3.5">
          {steps.map((step, i) => (
            <div
              key={i}
              className={`flex items-center gap-3 text-left transition-all duration-500 ${
                i <= currentStep ? 'opacity-100' : 'opacity-25'
              }`}
            >
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 text-xs font-bold transition-all duration-300 ${
                  i < currentStep
                    ? 'bg-green-500 text-white'
                    : i === currentStep
                    ? 'bg-orange-500 text-white'
                    : 'bg-slate-200 text-slate-400'
                }`}
              >
                {i < currentStep ? '✓' : i + 1}
              </div>
              <span
                className={`text-sm leading-tight ${
                  i <= currentStep ? 'text-slate-700 font-medium' : 'text-slate-400'
                }`}
              >
                {step}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Layout>
  )
}
