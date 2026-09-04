import type { AttentionComponents } from '../../types'
import { clsx } from 'clsx'

interface ScoreComponentsProps {
  components: AttentionComponents
}

const componentConfig = [
  { key: 'price' as const, label: 'Price Movement', weight: '35%' },
  { key: 'volume' as const, label: 'Volume Anomaly', weight: '20%' },
  { key: 'sentiment' as const, label: 'News / Sentiment', weight: '20%' },
  { key: 'volatility' as const, label: 'Volatility Change', weight: '15%' },
  { key: 'technical' as const, label: 'Technical Signal', weight: '10%' },
]

function BarColor(score: number) {
  if (score >= 75) return 'bg-red-500'
  if (score >= 50) return 'bg-orange-500'
  if (score >= 25) return 'bg-yellow-500'
  return 'bg-green-500'
}

export function ScoreComponents({ components }: ScoreComponentsProps) {
  return (
    <div className="bg-surface-card border border-surface-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-4">
        Score Breakdown
      </h3>
      <div className="space-y-3">
        {componentConfig.map(({ key, label, weight }) => {
          const score = components[key]
          return (
            <div key={key}>
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-slate-300">{label}</span>
                  <span className="text-xs text-slate-600">{weight}</span>
                </div>
                <span className={clsx(
                  'text-sm font-bold',
                  score >= 75 ? 'text-red-400' :
                  score >= 50 ? 'text-orange-400' :
                  score >= 25 ? 'text-yellow-400' :
                  'text-green-400'
                )}>
                  {score.toFixed(0)}
                </span>
              </div>
              <div className="h-1.5 bg-surface-border rounded-full overflow-hidden">
                <div
                  className={clsx('h-full rounded-full transition-all duration-700', BarColor(score))}
                  style={{ width: `${score}%` }}
                />
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
