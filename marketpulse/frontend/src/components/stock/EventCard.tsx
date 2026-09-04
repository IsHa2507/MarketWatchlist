import { ExternalLink, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import type { MarketEvent } from '../../types'
import { formatTimeAgo } from '../../utils/format'
import { clsx } from 'clsx'

interface EventCardProps {
  event: MarketEvent
}

export function EventCard({ event }: EventCardProps) {
  const sentiment = event.sentiment?.toLowerCase()

  const sentimentMap: Record<string, { label: string; color: string; bg: string; icon: React.ElementType }> = {
    positive: {
      label: 'Positive',
      color: 'text-green-400',
      bg: 'bg-green-900/20 border-green-900/40',
      icon: TrendingUp,
    },
    negative: {
      label: 'Negative',
      color: 'text-red-400',
      bg: 'bg-red-900/20 border-red-900/40',
      icon: TrendingDown,
    },
    neutral: {
      label: 'Neutral',
      color: 'text-slate-400',
      bg: 'bg-surface-elevated border-surface-border',
      icon: Minus,
    },
  }
  const sentimentConfig = sentimentMap[sentiment] ?? sentimentMap['neutral']

  const impactColor =
    event.impact_score >= 75 ? 'text-red-400' :
    event.impact_score >= 50 ? 'text-orange-400' :
    event.impact_score >= 25 ? 'text-yellow-400' :
    'text-slate-500'

  const impactLabel =
    event.impact_score >= 75 ? '🔴 High Impact' :
    event.impact_score >= 50 ? '🟠 Medium Impact' :
    event.impact_score >= 25 ? '🟡 Low Impact' :
    '⚪ Minimal'

  const Icon = sentimentConfig.icon

  return (
    <div className={clsx(
      'bg-surface-card border rounded-xl p-4 space-y-2',
      sentimentConfig.bg
    )}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2 flex-1 min-w-0">
          <Icon className={clsx('w-4 h-4 flex-shrink-0 mt-0.5', sentimentConfig.color)} />
          <div className="min-w-0">
            <p className="text-sm font-semibold text-white leading-snug">{event.title}</p>
            <div className="flex items-center gap-2 mt-1">
              <span className={clsx('text-xs font-medium', impactColor)}>{impactLabel}</span>
              <span className="text-xs text-slate-600">·</span>
              <span className="text-xs text-slate-500 capitalize">{event.event_type}</span>
            </div>
          </div>
        </div>
        <div className="flex-shrink-0 text-right">
          <p className="text-xs text-slate-500">{formatTimeAgo(event.timestamp)}</p>
          {event.source && (
            <p className="text-xs text-slate-600 mt-0.5">{event.source}</p>
          )}
        </div>
      </div>

      {event.description && (
        <p className="text-xs text-slate-400 leading-relaxed pl-6">
          {event.description}
        </p>
      )}
    </div>
  )
}
