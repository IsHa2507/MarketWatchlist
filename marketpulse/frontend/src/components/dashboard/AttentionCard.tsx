import { useNavigate } from 'react-router-dom'
import { TrendingUp, TrendingDown, ArrowRight, Volume2 } from 'lucide-react'
import type { AttentionScore } from '../../types'
import { ClassificationBadge, ScoreBadge } from '../ui/Badge'
import { FreshnessBadge } from '../ui/FreshnessBadge'
import { formatPercent, formatTimeAgo } from '../../utils/format'
import { clsx } from 'clsx'

interface AttentionCardProps {
  item: AttentionScore
  variant?: 'full' | 'compact'
}

export function AttentionCard({ item, variant = 'full' }: AttentionCardProps) {
  const navigate = useNavigate()
  const currency = item.stock_data?.currency === 'INR' ? '₹' : '$'
  const isUp = item.price_change_percent >= 0

  if (variant === 'compact') {
    return (
      <button
        onClick={() => navigate(`/stocks/${item.ticker}`)}
        className="w-full flex items-center justify-between p-3 bg-surface-elevated border border-surface-border rounded-lg hover:border-slate-600 transition-colors group"
      >
        <div className="flex items-center gap-3">
          <div className={clsx(
            'w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold',
            'bg-surface-border text-slate-300'
          )}>
            {item.ticker.slice(0, 2)}
          </div>
          <div className="text-left">
            <p className="text-sm font-semibold text-white">{item.ticker}</p>
            <p className="text-xs text-slate-500 truncate max-w-[120px]">{item.company_name}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className={clsx(
            'text-sm font-semibold',
            isUp ? 'text-green-400' : 'text-red-400'
          )}>
            {formatPercent(item.price_change_percent)}
          </span>
          <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-slate-400 transition-colors" />
        </div>
      </button>
    )
  }

  return (
    <button
      onClick={() => navigate(`/stocks/${item.ticker}`)}
      className={clsx(
        'w-full text-left bg-surface-card border rounded-xl p-5 hover:border-slate-600 transition-all group',
        item.classification === 'CRITICAL' ? 'border-red-900/60 hover:border-red-800' :
        item.classification === 'IMPORTANT' ? 'border-orange-900/60 hover:border-orange-800' :
        'border-surface-border'
      )}
    >
      <div className="flex items-start justify-between gap-4 mb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xl font-bold text-white">{item.ticker}</span>
            <ClassificationBadge classification={item.classification} />
          </div>
          <p className="text-sm text-slate-400">{item.company_name}</p>
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-lg font-bold text-white">
            {currency}{item.current_price.toLocaleString()}
          </p>
          <p className={clsx(
            'text-sm font-semibold flex items-center justify-end gap-1',
            isUp ? 'text-green-400' : 'text-red-400'
          )}>
            {isUp ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
            {formatPercent(item.price_change_percent)}
          </p>
          {item.since && (
            <p className="text-xs text-slate-600 mt-0.5">since {formatTimeAgo(item.since)}</p>
          )}
        </div>
      </div>

      {/* Score */}
      <div className="flex items-center gap-3 mb-4">
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs text-slate-500 uppercase tracking-wider">Attention Score</span>
            <ScoreBadge score={item.attention_score} size="sm" />
          </div>
          <div className="h-1.5 bg-surface-border rounded-full overflow-hidden">
            <div
              className={clsx(
                'h-full rounded-full transition-all',
                item.attention_score >= 81 ? 'bg-red-500' :
                item.attention_score >= 61 ? 'bg-orange-500' :
                item.attention_score >= 31 ? 'bg-yellow-500' : 'bg-green-500'
              )}
              style={{ width: `${item.attention_score}%` }}
            />
          </div>
        </div>
      </div>

      {/* Key reasons */}
      {item.key_reasons.length > 0 && (
        <ul className="space-y-1.5 mb-3">
          {item.key_reasons.map((reason, i) => (
            <li key={i} className="flex items-start gap-2 text-xs text-slate-400">
              <span className="mt-0.5 flex-shrink-0">•</span>
              {reason}
            </li>
          ))}
        </ul>
      )}

      {/* Volume indicator */}
      {item.volume_multiplier >= 1.5 && (
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <Volume2 className="w-3.5 h-3.5" />
          Volume {item.volume_multiplier.toFixed(1)}x average
        </div>
      )}

      <div className="flex items-center justify-between mt-3 pt-3 border-t border-surface-border">
        <FreshnessBadge
          freshness={item.freshness ?? item.stock_data?.freshness}
          demoMode={item.demo_mode ?? item.stock_data?.demo_mode}
        />
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">View analysis</span>
          <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-accent transition-colors" />
        </div>
      </div>
    </button>
  )
}
