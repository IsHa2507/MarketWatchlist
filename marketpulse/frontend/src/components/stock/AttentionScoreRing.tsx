import type { Classification } from '../../types'
import { classificationLabel } from '../../utils/format'
import { clsx } from 'clsx'

interface AttentionScoreRingProps {
  score: number
  classification: Classification
  size?: 'sm' | 'md' | 'lg'
}

export function AttentionScoreRing({ score, classification, size = 'lg' }: AttentionScoreRingProps) {
  const radius = size === 'lg' ? 52 : size === 'md' ? 38 : 28
  const strokeWidth = size === 'lg' ? 6 : 5
  const circumference = 2 * Math.PI * radius
  const progress = (score / 100) * circumference
  const dim = (radius + strokeWidth) * 2

  const ringColor =
    classification === 'CRITICAL' ? '#ef4444' :
    classification === 'IMPORTANT' ? '#f97316' :
    classification === 'WORTH_WATCHING' ? '#eab308' :
    '#22c55e'

  const textSize = size === 'lg' ? 'text-3xl' : size === 'md' ? 'text-xl' : 'text-base'
  const subSize = size === 'lg' ? 'text-xs' : 'text-[10px]'

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative inline-flex items-center justify-center">
        <svg width={dim} height={dim} style={{ transform: 'rotate(-90deg)' }}>
          {/* Background ring */}
          <circle
            cx={dim / 2}
            cy={dim / 2}
            r={radius}
            fill="none"
            stroke="#1e2535"
            strokeWidth={strokeWidth}
          />
          {/* Progress ring */}
          <circle
            cx={dim / 2}
            cy={dim / 2}
            r={radius}
            fill="none"
            stroke={ringColor}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={`${progress} ${circumference}`}
            style={{ transition: 'stroke-dasharray 0.8s ease' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={clsx('font-bold text-white leading-none', textSize)}>
            {score.toFixed(0)}
          </span>
          <span className={clsx('text-slate-500 leading-none mt-0.5', subSize)}>/100</span>
        </div>
      </div>
      <div className={clsx(
        'px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wide border',
        classification === 'CRITICAL' ? 'bg-red-900/40 text-red-300 border-red-800' :
        classification === 'IMPORTANT' ? 'bg-orange-900/40 text-orange-300 border-orange-800' :
        classification === 'WORTH_WATCHING' ? 'bg-yellow-900/40 text-yellow-300 border-yellow-800' :
        'bg-green-900/40 text-green-300 border-green-800'
      )}>
        {classificationLabel(classification)}
      </div>
    </div>
  )
}
