const config = {
  HIGH: { label: '고위험', bg: 'bg-red-100', text: 'text-red-600', dot: 'bg-red-500' },
  MED:  { label: '중위험', bg: 'bg-amber-100', text: 'text-amber-600', dot: 'bg-amber-500' },
  LOW:  { label: '저위험', bg: 'bg-green-100', text: 'text-green-600', dot: 'bg-green-500' },
}

export default function RiskBadge({ level }) {
  const c = config[level] ?? config.MED
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold ${c.bg} ${c.text} flex-shrink-0`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {c.label}
    </span>
  )
}
