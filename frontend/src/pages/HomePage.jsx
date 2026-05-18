import { useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, Camera, Image, History, Settings, TriangleAlert, Zap, Flame, Footprints, PackageOpen, Cog, FlaskConical } from 'lucide-react'
import Layout from '../components/Layout'

const hazardRow1 = [
  { label: '추락', icon: TriangleAlert, iconColor: 'text-orange-500', bg: 'bg-orange-100' },
  { label: '감전', icon: Zap, iconColor: 'text-blue-500', bg: 'bg-blue-100' },
  { label: '화재', icon: Flame, iconColor: 'text-red-500', bg: 'bg-red-100' },
]

const hazardRow2 = [
  { label: '넘어짐', icon: Footprints, iconColor: 'text-purple-500', bg: 'bg-purple-100' },
  { label: '낙하', icon: PackageOpen, iconColor: 'text-slate-600', bg: 'bg-slate-200' },
  { label: '끼임', icon: Cog, iconColor: 'text-yellow-600', bg: 'bg-yellow-100' },
  { label: '화학물질', icon: FlaskConical, iconColor: 'text-green-600', bg: 'bg-green-100' },
]

function HazardIcon({ label, icon: Icon, iconColor, bg, size = 14, iconSize }) {
  return (
    <div className="flex flex-col items-center gap-2">
      <div className={`rounded-full ${bg} flex items-center justify-center`} style={{ width: size * 4, height: size * 4 }}>
        <Icon size={iconSize ?? size * 1.8} className={iconColor} />
      </div>
      <span className="text-xs text-slate-600 font-medium">{label}</span>
    </div>
  )
}

export default function HomePage() {
  const navigate = useNavigate()
  const cameraInputRef = useRef(null)
  const fileInputRef = useRef(null)

  const handleFile = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const previewUrl = URL.createObjectURL(file)
    navigate('/preview', { state: { previewUrl, fileName: file.name } })
  }

  return (
    <Layout>
      {/* Header */}
      <header className="flex items-center justify-between px-5 pt-12 pb-4">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-full bg-blue-600 flex items-center justify-center">
            <Shield size={18} className="text-white" />
          </div>
          <span className="text-lg font-bold text-slate-900">Safety AI</span>
        </div>
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/history')} className="text-slate-500 active:text-slate-700">
            <History size={22} />
          </button>
          <button onClick={() => navigate('/admin')} className="text-slate-500 active:text-slate-700">
            <Settings size={22} />
          </button>
        </div>
      </header>

      {/* Hero */}
      <div className="flex-1 flex flex-col items-center justify-start px-5 pt-10 pb-6">
        <div className="w-24 h-24 rounded-[28px] bg-blue-100 flex items-center justify-center mb-5">
          <Shield size={44} className="text-blue-600" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900 text-center mb-2">AI Safety Inspector</h1>
        <p className="text-sm text-slate-500 text-center mb-8">
          사진 한 장으로 위험 요소를 자동 분석하세요
        </p>

        {/* Buttons */}
        <div className="w-full flex flex-col gap-3 mb-6">
          <button
            onClick={() => cameraInputRef.current?.click()}
            className="w-full bg-blue-600 text-white font-semibold py-4 rounded-2xl flex items-center justify-center gap-2 text-base active:bg-blue-700 transition-colors shadow-md shadow-blue-200"
          >
            <Camera size={20} />
            카메라로 촬영
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="w-full border-2 border-slate-200 text-slate-700 font-semibold py-4 rounded-2xl flex items-center justify-center gap-2 text-base active:bg-slate-50 transition-colors"
          >
            <Image size={20} />
            갤러리에서 선택
          </button>
        </div>

        {/* Hazard type card */}
        <div className="w-full bg-slate-50 rounded-2xl p-5 border border-slate-100">
          <p className="text-xs text-slate-500 text-center mb-4">AI가 자동으로 탐지하는 주요 위험 요소</p>
          <div className="flex flex-col gap-4">
            {/* 1행: 추락, 감전, 화재 */}
            <div className="flex justify-around">
              {hazardRow1.map((h) => <HazardIcon key={h.label} {...h} size={12} />)}
            </div>
            {/* 2행: 넘어짐, 낙하, 끼임, 화학물질 */}
            <div className="flex justify-around">
              {hazardRow2.map((h) => <HazardIcon key={h.label} {...h} size={12} />)}
            </div>
          </div>
        </div>

        <p className="text-xs text-slate-400 text-center mt-4 leading-relaxed">
          추락, 감전, 화재 등 7가지를 포함한 위험 요소를 자동 탐지하고<br />산업안전보건기준에 관한 규칙 기반으로 예방 방법을 제공합니다
        </p>
      </div>

      {/* Certification badge */}
      <div className="flex justify-center pb-6">
        <div className="flex items-center gap-1.5 border border-green-300 text-green-600 text-xs font-semibold px-4 py-2 rounded-full bg-green-50">
          <Shield size={13} />
          AI 안전 관리 인증
        </div>
      </div>

      <input ref={cameraInputRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handleFile} />
      <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleFile} />
    </Layout>
  )
}
