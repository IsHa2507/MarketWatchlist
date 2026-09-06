/**
 * FreshnessBadge
 *
 * Displays a compact data-freshness indicator based on the `freshness`
 * object returned by the backend.
 *
 * Variants:
 *   🟢 FRESH   — data is within the cache TTL
 *   🟡 STALE   — data is older than TTL but still usable
 *   ⚪ CLOSED  — market is closed; showing last session data
 *   🔴 ERROR   — data unavailable
 *
 * Also shows a "Demo" pill when demo_mode is true.
 * Does not redesign the surrounding UI — purely additive.
 */
import { clsx } from 'clsx'
import type { FreshnessInfo } from '../../types'

interface FreshnessBadgeProps {
  freshness?: FreshnessInfo | null
  demoMode?: boolean
  /** 'inline' (default) keeps badge on one line; 'block' adds a full row */
  layout?: 'inline' | 'block'
  className?: string
}

export function FreshnessBadge({
  freshness,
  demoMode = false,
  layout = 'inline',
  className,
}: FreshnessBadgeProps) {
  if (!freshness && !demoMode) return null

  return (
    <span className={clsx('inline-flex items-center gap-1.5', className)}>
      {freshness && <StatusPill freshness={freshness} />}
      {demoMode && <DemoPill />}
    </span>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatusPill({ freshness }: { freshness: FreshnessInfo }) {
  const { status, label, age_seconds, market_state } = freshness

  // Compute tooltip text
  let title = label
  if (age_seconds >= 0) {
    const mins = Math.floor(age_seconds / 60)
    title = mins < 1
      ? 'Updated just now'
      : `Updated ${mins} minute${mins !== 1 ? 's' : ''} ago`
    if (market_state === 'CLOSED' || market_state === 'POST') {
      title += ' — Market closed'
    }
  }

  const colorClass =
    status === 'FRESH'
      ? 'text-green-400 bg-green-900/20 border-green-800/40'
      : status === 'CLOSED'
      ? 'text-slate-400 bg-slate-800/40 border-slate-700/40'
      : status === 'ERROR'
      ? 'text-red-400 bg-red-900/20 border-red-800/40'
      : 'text-yellow-400 bg-yellow-900/20 border-yellow-800/40' // STALE

  return (
    <span
      title={title}
      className={clsx(
        'inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-medium border',
        colorClass,
      )}
    >
      <FreshnessDot status={status} />
      {label}
    </span>
  )
}

function FreshnessDot({ status }: { status: string }) {
  if (status === 'FRESH') return <span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block" />
  if (status === 'CLOSED') return <span className="w-1.5 h-1.5 rounded-full bg-slate-400 inline-block" />
  if (status === 'ERROR') return <span className="w-1.5 h-1.5 rounded-full bg-red-400 inline-block" />
  return <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 inline-block" /> // STALE
}

function DemoPill() {
  return (
    <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border text-purple-400 bg-purple-900/20 border-purple-800/40">
      Demo
    </span>
  )
}
