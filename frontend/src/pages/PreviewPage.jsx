import { useNavigate, useLocation } from 'react-router-dom'
import { ArrowLeft, Play, RotateCcw } from 'lucide-react'
import Layout from '../components/Layout'

export default function PreviewPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { previewUrl } = location.state ?? {}

  if (!previewUrl) {
    navigate('/')
    return null
  }

  const handleAnalyze = () => {
    // TODO: FormData로 이미지 업로드 → 분석 ID 받아서 state로 전달
    navigate('/analyzing', { state: { previewUrl } })
  }

  return (
    <Layout hideNav>
      <header className="flex items-center gap-3 px-5 pt-10 pb-4 border-b border-slate-100">
        <button onClick={() => navigate('/')} className="text-slate-500 active:text-slate-700">
          <ArrowLeft size={22} />
        </button>
        <h1 className="text-lg font-bold text-slate-900">사진 미리보기</h1>
      </header>

      <div className="flex-1 flex flex-col px-5 py-5 gap-4">
        {/* Image preview */}
        <div className="flex-1 rounded-2xl bg-blue-50 overflow-hidden flex items-center justify-center min-h-64">
          <img
            src={previewUrl}
            alt="미리보기"
            className="w-full h-full object-contain"
          />
        </div>

        {/* Buttons */}
        <div className="flex flex-col gap-3 pb-2">
          <button
            onClick={handleAnalyze}
            className="w-full bg-blue-600 text-white font-semibold py-4 rounded-2xl flex items-center justify-center gap-2 text-base active:bg-blue-700 transition-colors shadow-md shadow-blue-200"
          >
            <Play size={18} fill="white" />
            분석 시작
          </button>
          <button
            onClick={() => navigate('/')}
            className="w-full border-2 border-slate-200 text-slate-700 font-semibold py-4 rounded-2xl flex items-center justify-center gap-2 text-base active:bg-slate-50 transition-colors"
          >
            <RotateCcw size={18} />
            다시 촬영
          </button>
        </div>
      </div>
    </Layout>
  )
}
