import { clsx } from 'clsx'
import type { Classification } from '../../types'
import { classificationBadge, classificationLabel, classificationDot } from '../../utils/format'

interface BadgeProps {
  classification: Classification
  showDot?: boolean
  className?: string
}

export function ClassificationBadge({ classification, showDot = true, className }: BadgeProps) {
  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold tracking-wide uppercase',
      classificationBadge(classification),
      className
    )}>
      {showDot && <span>{classificationDot(classification)}</span>}
      {classificationLabel(classification)}
    </span>
  )
}

interface ScoreBadgeProps {
  score: number
  size?: 'sm' | 'md' | 'lg'
}

export function ScoreBadge({ score, size = 'md' }: ScoreBadgeProps) {
  const color =
    score >= 81 ? 'text-red-400 bg-red-900/30 border-red-800' :
    score >= 61 ? 'text-orange-400 bg-orange-900/30 border-orange-800' :
    score >= 31 ? 'text-yellow-400 bg-yellow-900/30 border-yellow-800' :
    'text-green-400 bg-green-900/30 border-green-800'

  const textSize = size === 'lg' ? 'text-3xl' : size === 'md' ? 'text-xl' : 'text-sm'
  const padding = size === 'lg' ? 'px-4 py-2' : 'px-2.5 py-1'

  return (
    <span className={clsx(
      'inline-flex items-baseline gap-1 rounded-lg border font-bold',
      color, textSize, padding
    )}>
      {score.toFixed(0)}
      {size !== 'sm' && <span className="text-xs font-normal opacity-60">/100</span>}
    </span>
  )
}

interface SentimentBadgeProps {
  sentiment: string
}

export function SentimentBadge({ sentiment }: SentimentBadgeProps) {
  const lower = sentiment.toLowerCase()
  const color =
    lower.includes('positive') ? 'bg-green-900/40 text-green-300 border-green-800' :
    lower.includes('negative') ? 'bg-red-900/40 text-red-300 border-red-800' :
    'bg-slate-800 text-slate-300 border-slate-700'

  return (
    <span className={clsx('inline-flex px-2 py-0.5 rounded text-xs font-medium border', color)}>
      {sentiment}
    </span>
  )
}
