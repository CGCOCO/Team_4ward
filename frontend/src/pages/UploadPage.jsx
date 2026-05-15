import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../components/Layout'

export default function UploadPage() {
  const navigate = useNavigate()
  const [preview, setPreview] = useState(null)
  const [file, setFile] = useState(null)
  const fileInputRef = useRef(null)
  const cameraInputRef = useRef(null)

  const handleFile = (e) => {
    const selected = e.target.files?.[0]
    if (!selected) return
    setFile(selected)
    setPreview(URL.createObjectURL(selected))
  }

  const handleAnalyze = () => {
    if (!file) return
    // TODO: FormData 업로드 → 분석 ID 받아서 navigate('/analyzing', { state: { analysisId } })
    navigate('/analyzing')
  }

  const clearFile = () => {
    setPreview(null)
    setFile(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
    if (cameraInputRef.current) cameraInputRef.current.value = ''
  }

  return (
    <Layout>
      <header className="px-5 pt-10 pb-4">
        <button onClick={() => navigate(-1)} className="text-slate-400 mb-3 flex items-center gap-1 text-sm">
          <span>←</span> 뒤로
        </button>
        <h1 className="text-xl font-bold text-slate-900">현장 사진 업로드</h1>
        <p className="text-sm text-slate-500 mt-1">분석할 현장 사진을 선택하세요</p>
      </header>

      <div className="flex-1 px-5 flex flex-col gap-4">
        {/* Upload/preview area */}
        {preview ? (
          <div className="relative rounded-2xl overflow-hidden bg-slate-100 aspect-[4/3]">
            <img src={preview} alt="업로드 이미지" className="w-full h-full object-cover" />
            <button
              onClick={clearFile}
              className="absolute top-3 right-3 bg-black/50 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold"
            >
              ✕
            </button>
            <div className="absolute bottom-3 left-3 bg-black/50 text-white text-xs px-2 py-1 rounded-full">
              {file?.name}
            </div>
          </div>
        ) : (
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-slate-300 bg-slate-50 aspect-[4/3] active:bg-slate-100 transition-colors cursor-pointer"
          >
            <div className="text-5xl mb-3">🖼️</div>
            <p className="text-sm font-semibold text-slate-600">사진을 탭해서 선택하세요</p>
            <p className="text-xs text-slate-400 mt-1">JPG · PNG · HEIC 지원</p>
          </button>
        )}

        {/* Action buttons */}
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => cameraInputRef.current?.click()}
            className="flex items-center justify-center gap-2 py-3.5 rounded-xl bg-slate-100 text-slate-700 font-medium text-sm active:bg-slate-200 transition-colors"
          >
            <span className="text-lg">📷</span>
            <span>카메라 촬영</span>
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center justify-center gap-2 py-3.5 rounded-xl bg-slate-100 text-slate-700 font-medium text-sm active:bg-slate-200 transition-colors"
          >
            <span className="text-lg">🖼️</span>
            <span>갤러리 선택</span>
          </button>
        </div>

        {/* Privacy notice */}
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <p className="text-xs text-amber-700 font-semibold mb-1 flex items-center gap-1">
            <span>🔒</span> 개인정보 보호 안내
          </p>
          <p className="text-xs text-amber-600 leading-relaxed">
            업로드된 이미지는 OpenCV를 통해 얼굴 등 개인정보가 자동으로 마스킹된 후 분석됩니다.
          </p>
        </div>

        {/* Analyze button */}
        <button
          onClick={handleAnalyze}
          disabled={!file}
          className={`w-full py-4 rounded-2xl font-bold text-base transition-all ${
            file
              ? 'bg-orange-500 text-white shadow-lg shadow-orange-200 active:scale-95'
              : 'bg-slate-200 text-slate-400 cursor-not-allowed'
          }`}
        >
          🔍 AI 안전 진단 시작
        </button>
      </div>

      <input ref={fileInputRef} type="file" accept="image/*" className="hidden" onChange={handleFile} />
      <input ref={cameraInputRef} type="file" accept="image/*" capture="environment" className="hidden" onChange={handleFile} />
    </Layout>
  )
}
