import type { Classification } from '../types'

export function formatPrice(price: number, currency = 'USD'): string {
  const symbol = currency === 'INR' ? '₹' : '$'
  return `${symbol}${price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export function formatPercent(value: number, showSign = true): string {
  const sign = showSign && value > 0 ? '+' : ''
  return `${sign}${value.toFixed(2)}%`
}

export function formatVolume(volume: number): string {
  if (volume >= 1_000_000) return `${(volume / 1_000_000).toFixed(1)}M`
  if (volume >= 1_000) return `${(volume / 1_000).toFixed(0)}K`
  return volume.toFixed(0)
}

export function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffMins < 1) return 'just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays === 1) return 'yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

export function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}

export function classificationLabel(c: Classification): string {
  switch (c) {
    case 'CRITICAL': return 'Critical'
    case 'IMPORTANT': return 'Important'
    case 'WORTH_WATCHING': return 'Worth Watching'
    case 'NORMAL': return 'Normal'
  }
}

export function classificationColor(c: Classification): string {
  switch (c) {
    case 'CRITICAL': return 'text-red-400'
    case 'IMPORTANT': return 'text-orange-400'
    case 'WORTH_WATCHING': return 'text-yellow-400'
    case 'NORMAL': return 'text-green-400'
  }
}

export function classificationBadge(c: Classification): string {
  switch (c) {
    case 'CRITICAL':
      return 'bg-red-900/50 text-red-300 border border-red-800'
    case 'IMPORTANT':
      return 'bg-orange-900/50 text-orange-300 border border-orange-800'
    case 'WORTH_WATCHING':
      return 'bg-yellow-900/50 text-yellow-300 border border-yellow-800'
    case 'NORMAL':
      return 'bg-green-900/50 text-green-300 border border-green-800'
  }
}

export function classificationDot(c: Classification): string {
  switch (c) {
    case 'CRITICAL': return '🔴'
    case 'IMPORTANT': return '🟠'
    case 'WORTH_WATCHING': return '🟡'
    case 'NORMAL': return '🟢'
  }
}

export function sentimentColor(label: string): string {
  const l = label.toLowerCase()
  if (l.includes('positive')) return 'text-green-400'
  if (l.includes('negative')) return 'text-red-400'
  return 'text-slate-400'
}

export function getGreeting(): string {
  const h = new Date().getHours()
  if (h < 12) return 'Good morning'
  if (h < 17) return 'Good afternoon'
  return 'Good evening'
}
