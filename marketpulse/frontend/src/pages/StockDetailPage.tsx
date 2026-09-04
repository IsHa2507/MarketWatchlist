import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft, Plus, Check, RefreshCw, TrendingUp, TrendingDown,
  Clock, Database, AlertTriangle,
} from 'lucide-react'
import { stockApi, dashboardApi, getErrorMessage } from '../services/api'
import { useWatchlists } from '../hooks/useWatchlist'
import { AppLayout } from '../components/layout/AppLayout'
import { PriceChart } from '../components/charts/PriceChart'
import { VolumeChart } from '../components/charts/VolumeChart'
import { ChangeBreakdown } from '../components/stock/ChangeBreakdown'
import { WhyItMatters } from '../components/stock/WhyItMatters'
import { AttentionScoreRing } from '../components/stock/AttentionScoreRing'
import { ScoreComponents } from '../components/stock/ScoreComponents'
import { EventCard } from '../components/stock/EventCard'
import { Skeleton } from '../components/ui/Skeleton'
import { Alert } from '../components/ui/Alert'
import { SentimentBadge } from '../components/ui/Badge'
import type { AttentionScore, HistoryDataPoint, MarketEvent, StockQuote } from '../types'
import { formatPercent, formatTimeAgo, classificationDot } from '../utils/format'
import { clsx } from 'clsx'

export function StockDetailPage() {
  const { ticker } = useParams<{ ticker: string }>()
  const navigate = useNavigate()
  const { watchlists, addStock, removeStock } = useWatchlists()

  const [quote, setQuote] = useState<StockQuote | null>(null)
  const [history, setHistory] = useState<HistoryDataPoint[]>([])
  const [events, setEvents] = useState<MarketEvent[]>([])
  const [attentionData, setAttentionData] = useState<AttentionScore | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(30)

  // Which watchlist this stock belongs to (if any)
  const activeWatchlist = watchlists[0]
  const isInWatchlist = activeWatchlist?.stocks.some((s) => s.ticker === ticker?.toUpperCase())
  const [adding, setAdding] = useState(false)

  useEffect(() => {
    if (!ticker) return
    fetchAll(ticker.toUpperCase())
  }, [ticker, days])

  const fetchAll = async (t: string) => {
    setLoading(true)
    setError(null)
    try {
      const [quoteRes, historyRes, eventsRes] = await Promise.allSettled([
        stockApi.get(t),
        stockApi.history(t, days),
        stockApi.events(t),
      ])

      if (quoteRes.status === 'fulfilled') setQuote(quoteRes.value.data)
      if (historyRes.status === 'fulfilled') setHistory(historyRes.value.data.data_points || [])
      if (eventsRes.status === 'fulfilled') setEvents(eventsRes.value.data.events || [])

      // Fetch attention data from dashboard
      try {
        const dashRes = await dashboardApi.get()
        const allStocks = [
          ...dashRes.data.needs_attention,
          ...dashRes.data.worth_watching,
          ...dashRes.data.normal,
        ]
        const found = allStocks.find((s: AttentionScore) => s.ticker === t)
        if (found) setAttentionData(found)
      } catch {
        // Non-fatal — dashboard data might not be available
      }
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const handleWatchlistToggle = async () => {
    if (!activeWatchlist || !ticker) return
    setAdding(true)
    try {
      if (isInWatchlist) {
        await removeStock(activeWatchlist.id, ticker.toUpperCase())
      } else {
        await addStock(activeWatchlist.id, ticker.toUpperCase())
      }
    } catch {
      // ignore
    } finally {
      setAdding(false)
    }
  }

  const t = ticker?.toUpperCase() || ''
  const currency = quote?.currency === 'INR' ? '₹' : '$'
  const isUp = (quote?.price_change_percent || 0) >= 0

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
        {/* Back */}
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-300 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back
        </button>

        {error && (
          <Alert
            variant="error"
            title="Unable to fetch market data"
            message={`${error} Showing latest available snapshot.`}
          />
        )}

        {loading ? (
          <StockDetailSkeleton />
        ) : quote ? (
          <>
            {/* Hero */}
            <div className="bg-surface-card border border-surface-border rounded-2xl p-6">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-3 mb-1">
                    <h1 className="text-3xl font-bold text-white">{t}</h1>
                    {attentionData && (
                      <span className="text-lg">{classificationDot(attentionData.classification)}</span>
                    )}
                  </div>
                  <p className="text-slate-400">{quote.company_name}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-xs text-slate-600 bg-surface-elevated px-2 py-0.5 rounded">
                      {quote.sector}
                    </span>
                    <SentimentBadge sentiment={quote.sentiment_label} />
                  </div>
                </div>

                <div className="flex flex-col items-end gap-2">
                  <p className="text-3xl font-bold text-white">
                    {currency}{quote.price.toLocaleString()}
                  </p>
                  <p className={clsx(
                    'flex items-center gap-1.5 text-lg font-semibold',
                    isUp ? 'text-green-400' : 'text-red-400'
                  )}>
                    {isUp ? <TrendingUp className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
                    {formatPercent(quote.price_change_percent)}
                  </p>
                  {attentionData?.since && (
                    <p className="text-xs text-slate-600 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Since {formatTimeAgo(attentionData.since)}
                    </p>
                  )}
                </div>
              </div>

              {/* Data confidence */}
              <div className="flex items-center justify-between mt-4 pt-4 border-t border-surface-border">
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <Database className="w-3.5 h-3.5" />
                  Data Confidence:
                  <span className={clsx(
                    'font-semibold',
                    quote.data_confidence === 'HIGH' ? 'text-green-400' : 'text-yellow-400'
                  )}>
                    {quote.data_confidence}
                  </span>
                  {quote.demo_mode && (
                    <span className="ml-1 text-slate-600">(demo mode)</span>
                  )}
                </div>
                <button
                  onClick={() => fetchAll(t)}
                  className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
                >
                  <RefreshCw className="w-3 h-3" />
                  Refresh
                </button>
              </div>
            </div>

            {/* Attention Score + Watchlist add */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {/* Score ring */}
              <div className="sm:col-span-1 bg-surface-card border border-surface-border rounded-xl p-6 flex flex-col items-center justify-center gap-3">
                {attentionData ? (
                  <AttentionScoreRing
                    score={attentionData.attention_score}
                    classification={attentionData.classification}
                    size="lg"
                  />
                ) : (
                  <div className="text-center text-slate-500 text-sm">
                    <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-30" />
                    <p>Visit the dashboard to<br />generate an attention score.</p>
                  </div>
                )}
              </div>

              {/* Quick stats */}
              <div className="sm:col-span-2 bg-surface-card border border-surface-border rounded-xl p-5 grid grid-cols-2 gap-4">
                <StatItem label="Volume" value={`${(quote.volume / 1_000_000).toFixed(1)}M`} sub={`Avg: ${(quote.average_volume / 1_000_000).toFixed(1)}M`} />
                <StatItem label="Vol / Avg" value={attentionData ? `${attentionData.volume_multiplier.toFixed(1)}x` : `${(quote.volume / quote.average_volume).toFixed(1)}x`} />
                <StatItem label="Volatility" value={(quote.volatility * 100).toFixed(2) + '%'} />
                <StatItem label="Sentiment" value={quote.sentiment_label}
                  valueClass={
                    quote.sentiment_label === 'Positive' ? 'text-green-400' :
                    quote.sentiment_label === 'Negative' ? 'text-red-400' : 'text-slate-300'
                  }
                />
              </div>
            </div>

            {/* Watchlist toggle */}
            {activeWatchlist && (
              <button
                onClick={handleWatchlistToggle}
                disabled={adding}
                className={clsx(
                  'w-full flex items-center justify-center gap-2 py-3 rounded-xl border text-sm font-medium transition-all',
                  isInWatchlist
                    ? 'bg-accent/10 border-accent/40 text-accent hover:bg-red-950/30 hover:border-red-800 hover:text-red-400'
                    : 'bg-surface-elevated border-surface-border text-slate-300 hover:border-accent/50 hover:text-white'
                )}
              >
                {isInWatchlist ? (
                  <><Check className="w-4 h-4" /> In watchlist — click to remove</>
                ) : (
                  <><Plus className="w-4 h-4" /> Add to {activeWatchlist.name}</>
                )}
              </button>
            )}

            {/* Change breakdown */}
            {attentionData && (
              <ChangeBreakdown data={attentionData} />
            )}

            {/* Why it matters */}
            {attentionData && (
              <WhyItMatters item={attentionData} />
            )}

            {/* Score components */}
            {attentionData && (
              <ScoreComponents components={attentionData.components} />
            )}

            {/* Price chart */}
            <div className="bg-surface-card border border-surface-border rounded-xl p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-white">Price History</h3>
                <div className="flex gap-1">
                  {[7, 14, 30, 90].map((d) => (
                    <button
                      key={d}
                      onClick={() => setDays(d)}
                      className={clsx(
                        'px-2.5 py-1 rounded-md text-xs font-medium transition-colors',
                        days === d
                          ? 'bg-accent text-white'
                          : 'text-slate-500 hover:text-slate-300 hover:bg-surface-elevated'
                      )}
                    >
                      {d}D
                    </button>
                  ))}
                </div>
              </div>
              <PriceChart data={history} currency={quote.currency} ticker={t} />
              {history.length > 0 && attentionData?.since && (
                <p className="text-xs text-blue-400/60 mt-2 flex items-center gap-1">
                  <span className="w-4 h-px bg-blue-400 border-dashed inline-block" />
                  Blue dashed line = your last check
                </p>
              )}
            </div>

            {/* Volume chart */}
            <div className="bg-surface-card border border-surface-border rounded-xl p-5">
              <h3 className="text-sm font-semibold text-white mb-4">Volume</h3>
              <VolumeChart data={history} averageVolume={quote.average_volume} />
            </div>

            {/* Events */}
            {events.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-white">News &amp; Events</h3>
                {events.map((ev, i) => (
                  <EventCard key={ev.id ?? i} event={ev} />
                ))}
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-16 text-slate-500">
            <p className="text-lg font-medium text-white mb-2">Stock not found</p>
            <p className="text-sm">{t} is not in our supported list.</p>
          </div>
        )}
      </div>
    </AppLayout>
  )
}

function StatItem({
  label, value, sub, valueClass,
}: {
  label: string
  value: string
  sub?: string
  valueClass?: string
}) {
  return (
    <div>
      <p className="text-xs text-slate-500 mb-1">{label}</p>
      <p className={clsx('text-base font-bold text-white', valueClass)}>{value}</p>
      {sub && <p className="text-xs text-slate-600">{sub}</p>}
    </div>
  )
}

function StockDetailSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-40 rounded-2xl" />
      <div className="grid grid-cols-3 gap-4">
        <Skeleton className="h-32 rounded-xl" />
        <Skeleton className="col-span-2 h-32 rounded-xl" />
      </div>
      <Skeleton className="h-64 rounded-xl" />
      <Skeleton className="h-32 rounded-xl" />
    </div>
  )
}
