import { useNavigate } from 'react-router-dom'
import { TrendingUp, TrendingDown, ArrowRight } from 'lucide-react'
import type { AttentionScore } from '../../types'
import { ScoreBadge } from '../ui/Badge'
import { formatPercent, formatTimeAgo } from '../../utils/format'
import { clsx } from 'clsx'

export function WatchingCard({ item }: { item: AttentionScore }) {
  const navigate = useNavigate()
  const isUp = item.price_change_percent >= 0
  const currency = item.stock_data?.currency === 'INR' ? '₹' : '$'

  return (
    <button
      onClick={() => navigate(`/stocks/${item.ticker}`)}
      className="w-full text-left bg-surface-card border border-yellow-900/40 rounded-xl p-4 hover:border-yellow-800/60 transition-all group"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-yellow-900/30 border border-yellow-800/50 flex items-center justify-center">
            <span className="text-xs font-bold text-yellow-400">{item.ticker.slice(0, 2)}</span>
          </div>
          <div>
            <p className="font-semibold text-white text-sm">{item.ticker}</p>
            <p className="text-xs text-slate-500 truncate max-w-[140px]">{item.company_name}</p>
          </div>
        </div>

        <div className="text-right">
          <p className="text-sm font-medium text-white">{currency}{item.current_price.toLocaleString()}</p>
          <p className={clsx(
            'text-xs font-semibold flex items-center justify-end gap-1',
            isUp ? 'text-green-400' : 'text-red-400'
          )}>
            {isUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
            {formatPercent(item.price_change_percent)}
          </p>
        </div>
      </div>

      <div className="flex items-center justify-between mt-3">
        <div className="flex flex-wrap gap-1.5">
          {item.volume_multiplier >= 1.4 && (
            <span className="text-xs bg-yellow-900/30 text-yellow-400 border border-yellow-800/50 px-2 py-0.5 rounded">
              Vol ↑{item.volume_multiplier.toFixed(1)}x
            </span>
          )}
          {item.sentiment_change !== 'Neutral' && (
            <span className="text-xs bg-surface-elevated text-slate-400 border border-surface-border px-2 py-0.5 rounded">
              {item.sentiment_label}
            </span>
          )}
          {item.since && (
            <span className="text-xs text-slate-600">since {formatTimeAgo(item.since)}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <ScoreBadge score={item.attention_score} size="sm" />
          <ArrowRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-yellow-400 transition-colors" />
        </div>
      </div>
    </button>
  )
}
