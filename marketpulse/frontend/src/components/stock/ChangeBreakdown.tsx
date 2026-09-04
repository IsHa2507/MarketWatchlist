import { TrendingUp, TrendingDown, Volume2, Activity, MessageCircle } from 'lucide-react'
import type { AttentionScore } from '../../types'
import { formatPercent } from '../../utils/format'
import { clsx } from 'clsx'

interface ChangeBreakdownProps {
  data: AttentionScore
  checkpointPrice?: number
}

function ChangeRow({
  label,
  value,
  sublabel,
  direction,
  icon: Icon,
}: {
  label: string
  value: string
  sublabel?: string
  direction?: 'up' | 'down' | 'neutral'
  icon: React.ElementType
}) {
  const color =
    direction === 'up' ? 'text-green-400' :
    direction === 'down' ? 'text-red-400' :
    'text-slate-400'

  const ArrowIcon = direction === 'up' ? TrendingUp : direction === 'down' ? TrendingDown : null

  return (
    <div className="flex items-center justify-between py-3 border-b border-surface-border last:border-0">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-surface-elevated rounded-lg flex items-center justify-center">
          <Icon className="w-4 h-4 text-slate-500" />
        </div>
        <div>
          <p className="text-sm font-medium text-slate-300">{label}</p>
          {sublabel && <p className="text-xs text-slate-600">{sublabel}</p>}
        </div>
      </div>
      <div className={clsx('flex items-center gap-1.5 font-semibold text-sm', color)}>
        {ArrowIcon && <ArrowIcon className="w-3.5 h-3.5" />}
        {value}
      </div>
    </div>
  )
}

export function ChangeBreakdown({ data, checkpointPrice }: ChangeBreakdownProps) {
  const priceChange = data.price_change_percent
  const priceDirection = priceChange > 0.5 ? 'up' : priceChange < -0.5 ? 'down' : 'neutral'
  const volMulti = data.volume_multiplier
  const volDirection = volMulti >= 1.3 ? 'up' : volMulti <= 0.7 ? 'down' : 'neutral'

  const sentimentRaw = data.sentiment_change
  const sentimentHasArrow = sentimentRaw.includes('→')
  const sentimentDirection = sentimentRaw.toLowerCase().includes('negative')
    ? 'down'
    : sentimentRaw.toLowerCase().includes('positive')
    ? 'up'
    : 'neutral'

  const cp = checkpointPrice || data.checkpoint_price
  const priceFrom = cp ? `From ${data.stock_data?.currency === 'INR' ? '₹' : '$'}${cp.toLocaleString()}` : undefined

  return (
    <div className="bg-surface-card border border-surface-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-1">
        Since You Last Checked
      </h3>
      <div>
        <ChangeRow
          label="Price"
          value={formatPercent(priceChange)}
          sublabel={priceFrom}
          direction={priceDirection}
          icon={TrendingUp}
        />
        <ChangeRow
          label="Volume"
          value={`${volMulti >= 1 ? '↑' : '↓'} ${Math.abs((volMulti - 1) * 100).toFixed(0)}%`}
          sublabel={`${volMulti.toFixed(1)}x average`}
          direction={volDirection}
          icon={Volume2}
        />
        <ChangeRow
          label="Volatility"
          value={data.components.volatility > 50 ? '↑ Elevated' : '↓ Normal'}
          direction={data.components.volatility > 50 ? 'down' : 'neutral'}
          icon={Activity}
        />
        <ChangeRow
          label="Sentiment"
          value={sentimentHasArrow ? sentimentRaw : data.sentiment_label}
          direction={sentimentDirection}
          icon={MessageCircle}
        />
      </div>
    </div>
  )
}
