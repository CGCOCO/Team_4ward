import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { ScanSearch, Brain, FileCheck, Lightbulb, Shield, Loader } from 'lucide-react'
import axios from 'axios'
import Layout from '../components/Layout'

const steps = [
  { label: '이미지 전처리 및 개인정보 마스킹', icon: ScanSearch },
  { label: '위험 요소 감지 중', icon: Brain },
  { label: '산업안전보건규칙 대조 중', icon: FileCheck },
  { label: '예방 조치 생성 중', icon: Lightbulb },
  { label: '위험성 평가 보고서 작성 중', icon: Shield },
]

const MIN_ANIM_MS = steps.length * 1200 + 800

export default function AnalyzingPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { previewUrl, file } = location.state ?? {}
  const [currentStep, setCurrentStep] = useState(0)

  useEffect(() => {
    const stepTimers = steps.map((_, i) =>
      setTimeout(() => setCurrentStep(i), i * 1200)
    )

    const apiCall = file
      ? axios.post('http://localhost:8001/api/v1/analyze', (() => {
          const fd = new FormData()
          fd.append('file', file)
          return fd
        })())
      : Promise.resolve({ data: null })

    const animDone = new Promise((res) => setTimeout(res, MIN_ANIM_MS))

    Promise.all([apiCall, animDone])
      .then(([response]) => {
        navigate('/result', { state: { previewUrl, result: response.data } })
      })
      .catch(() => {
        // API 실패 시 mock 데이터로 결과 페이지 이동
        navigate('/result', { state: { previewUrl, result: null } })
      })

    return () => stepTimers.forEach(clearTimeout)
  }, [])

  const { label, icon: Icon } = steps[currentStep]

  return (
    <Layout hideNav>
      <div className="flex-1 flex flex-col items-center justify-center px-8 text-center">

        {/* 상단: 아이콘 */}
        <div className="relative flex items-center justify-center mb-6">
          <div className="absolute w-44 h-44 rounded-full border-2 border-blue-200" />
          <div className="w-32 h-32 rounded-full bg-blue-100 flex items-center justify-center">
            <Icon size={52} className="text-blue-500" strokeWidth={1.5} />
          </div>
        </div>

        {/* 현재 단계 텍스트 */}
        <div className="flex items-center justify-center gap-2 mb-1.5">
          <Loader size={15} className="text-slate-400 animate-spin flex-shrink-0" />
          <p className="text-base font-semibold text-slate-800">{label}</p>
        </div>
        <p className="text-sm text-slate-400 mb-8">AI가 사진을 분석하고 있습니다</p>

        {/* 하단: 순차 체크 리스트 */}
        <div className="w-full max-w-xs flex flex-col gap-3 mb-8">
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
                    ? 'bg-blue-500 text-white'
                    : 'bg-slate-200 text-slate-400'
                }`}
              >
                {i < currentStep ? '✓' : i + 1}
              </div>
              <span className={`text-sm leading-tight ${
                i <= currentStep ? 'text-slate-700 font-medium' : 'text-slate-400'
              }`}>
                {step.label}
              </span>
            </div>
          ))}
        </div>

        {/* 점 인디케이터 */}
        <div className="flex items-center gap-2">
          {steps.map((_, i) => (
            <div
              key={i}
              className={`rounded-full transition-all duration-500 ${
                i <= currentStep ? 'w-2.5 h-2.5 bg-blue-500' : 'w-2 h-2 bg-slate-300'
              }`}
            />
          ))}
        </div>

      </div>
    </Layout>
  )
}
