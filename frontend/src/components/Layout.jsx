import BottomNav from './BottomNav'

export default function Layout({ children, hideNav = false }) {
  return (
    <div className="flex justify-center min-h-svh bg-slate-100">
      <div className={`relative w-full max-w-[430px] min-h-svh bg-white flex flex-col ${!hideNav ? 'pb-16' : ''}`}>
        {children}
        {!hideNav && <BottomNav />}
      </div>
    </div>
  )
}
