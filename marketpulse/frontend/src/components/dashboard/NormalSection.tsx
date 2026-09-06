import { useNavigate } from 'react-router-dom'
import { CheckCircle2, ArrowRight } from 'lucide-react'
import type { AttentionScore } from '../../types'
import { FreshnessBadge } from '../ui/FreshnessBadge'
import { formatPercent } from '../../utils/format'
import { clsx } from 'clsx'

export function NormalSection({ items }: { items: AttentionScore[] }) {
  const navigate = useNavigate()

  if (items.length === 0) return null

  return (
    <section>
      <div className="flex items-center gap-2 mb-4">
        <CheckCircle2 className="w-5 h-5 text-green-500" />
        <h2 className="text-lg font-semibold text-white">Nothing Significant</h2>
        <span className="text-sm text-slate-500">({items.length})</span>
      </div>

      <div className="bg-surface-card border border-surface-border rounded-xl overflow-hidden">
        <div className="px-4 py-3 bg-green-950/30 border-b border-green-900/30">
          <p className="text-sm text-green-400">
            These stocks haven't experienced meaningful changes since your last check.
          </p>
        </div>
        <ul className="divide-y divide-surface-border">
          {items.map((item) => {
            const isUp = item.price_change_percent >= 0
            const currency = item.stock_data?.currency === 'INR' ? '₹' : '$'
            return (
              <li key={item.ticker}>
                <button
                  onClick={() => navigate(`/stocks/${item.ticker}`)}
                  className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-elevated transition-colors group text-left"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-7 h-7 rounded-md bg-green-900/20 border border-green-900/40 flex items-center justify-center">
                      <span className="text-xs font-bold text-green-500">{item.ticker.slice(0, 1)}</span>
                    </div>
                    <div>
                      <span className="text-sm font-medium text-white">{item.ticker}</span>
                      <span className="ml-2 text-xs text-slate-500 hidden sm:inline">{item.company_name}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <FreshnessBadge
                      freshness={item.freshness ?? item.stock_data?.freshness}
                      demoMode={item.demo_mode ?? item.stock_data?.demo_mode}
                      className="hidden sm:inline-flex"
                    />
                    <span className="text-sm text-slate-400 hidden sm:block">
                      {currency}{item.current_price.toLocaleString()}
                    </span>
                    <span className={clsx(
                      'text-sm font-medium w-14 text-right',
                      isUp ? 'text-green-500' : 'text-red-500'
                    )}>
                      {formatPercent(item.price_change_percent)}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-slate-700 group-hover:text-slate-400 transition-colors" />
                  </div>
                </button>
              </li>
            )
          })}
        </ul>
      </div>
    </section>
  )
}
