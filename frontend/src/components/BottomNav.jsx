import { useNavigate, useLocation } from 'react-router-dom'
import { Home, Camera, FileText, Settings } from 'lucide-react'

const tabs = [
  { path: '/', label: '홈', icon: Home },
  { path: '/result', label: '진단', icon: Camera },
  { path: '/history', label: '이력', icon: FileText },
  { path: '/admin', label: '관리', icon: Settings },
]

export default function BottomNav() {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <nav className="fixed bottom-0 left-1/2 -translate-x-1/2 w-full max-w-[430px] bg-white border-t border-slate-200 flex z-50">
      {tabs.map(({ path, label, icon: Icon }) => {
        const active = location.pathname === path
        return (
          <button
            key={path}
            onClick={() => navigate(path)}
            className={`flex-1 flex flex-col items-center justify-center py-2.5 gap-1 text-xs font-medium transition-colors ${
              active ? 'text-blue-600' : 'text-slate-400'
            }`}
          >
            <Icon size={22} />
            <span>{label}</span>
          </button>
        )
      })}
    </nav>
  )
}
