import RiskBadge from './RiskBadge'

export default function HazardCard({ title, desc, level, regulation }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 flex flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-semibold text-slate-800 leading-snug">{title}</p>
        <RiskBadge level={level} />
      </div>
      <p className="text-xs text-slate-500 leading-relaxed">{desc}</p>
      {regulation && (
        <p className="text-xs text-orange-600 font-medium bg-orange-50 rounded-lg px-3 py-2">
          ⚖️ {regulation}
        </p>
      )}
    </div>
  )
}
