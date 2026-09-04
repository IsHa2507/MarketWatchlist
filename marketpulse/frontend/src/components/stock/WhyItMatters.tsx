import { Lightbulb, AlertTriangle, Info } from 'lucide-react'
import type { AttentionScore } from '../../types'
import { clsx } from 'clsx'

interface WhyItMattersProps {
  item: AttentionScore
}

export function WhyItMatters({ item }: WhyItMattersProps) {
  const isCritical = item.classification === 'CRITICAL'
  const isImportant = item.classification === 'IMPORTANT'

  const headerColor =
    isCritical ? 'text-red-400 bg-red-950/40 border-red-900/50' :
    isImportant ? 'text-orange-400 bg-orange-950/40 border-orange-900/50' :
    'text-yellow-400 bg-yellow-950/40 border-yellow-900/50'

  const Icon = isCritical || isImportant ? AlertTriangle : Lightbulb

  const impactLabel =
    item.attention_score >= 81 ? 'Critical Impact' :
    item.attention_score >= 61 ? 'High Impact' :
    item.attention_score >= 31 ? 'Moderate Impact' :
    'Low Impact'

  return (
    <div className="bg-surface-card border border-surface-border rounded-xl overflow-hidden">
      {/* Header */}
      <div className={clsx('px-5 py-3 border-b flex items-center gap-2', headerColor)}>
        <Icon className="w-4 h-4" />
        <span className="text-xs font-bold uppercase tracking-wider">Why It Matters</span>
        <span className="ml-auto text-xs font-semibold opacity-80">{impactLabel}</span>
      </div>

      {/* Body */}
      <div className="px-5 py-4 space-y-4">
        {/* Explanation text */}
        <p className="text-sm text-slate-300 leading-relaxed">
          {item.explanation}
        </p>

        {/* Key reasons */}
        {item.key_reasons.length > 0 && (
          <ul className="space-y-2">
            {item.key_reasons.map((reason, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-slate-400">
                <span className="mt-1 w-1.5 h-1.5 rounded-full bg-slate-600 flex-shrink-0" />
                {reason}
              </li>
            ))}
          </ul>
        )}

        {/* Disclaimer */}
        <div className="flex items-start gap-2 text-xs text-slate-600 pt-2 border-t border-surface-border">
          <Info className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
          <span>
            MarketPulse provides market awareness information only. This is not investment advice.
            Always do your own research before making any financial decisions.
          </span>
        </div>
      </div>
    </div>
  )
}
