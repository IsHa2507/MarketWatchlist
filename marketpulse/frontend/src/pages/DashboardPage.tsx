import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  RefreshCw, Clock, AlertTriangle, Activity, TrendingUp,
  Search, Plus, Calendar,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useDashboard } from '../hooks/useDashboard'
import { useWatchlists } from '../hooks/useWatchlist'
import { AppLayout } from '../components/layout/AppLayout'
import { AttentionCard } from '../components/dashboard/AttentionCard'
import { WatchingCard } from '../components/dashboard/WatchingCard'
import { NormalSection } from '../components/dashboard/NormalSection'
import { WatchlistSidebar } from '../components/dashboard/WatchlistSidebar'
import { DashboardSkeleton } from '../components/ui/Skeleton'
import { Alert } from '../components/ui/Alert'
import { getGreeting, formatDate, formatTimeAgo } from '../utils/format'
import { clsx } from 'clsx'

export function DashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const {
    watchlists,
    loading: wlLoading,
    createWatchlist,
    updateWatchlist,
    deleteWatchlist,
  } = useWatchlists()

  const [activeWatchlistId, setActiveWatchlistId] = useState<number | undefined>()

  // Once watchlists load, default to the first one
  useEffect(() => {
    if (!activeWatchlistId && watchlists.length > 0) {
      setActiveWatchlistId(watchlists[0].id)
    }
  }, [watchlists, activeWatchlistId])

  const { data, loading, error, refetch, lastFetch } = useDashboard(activeWatchlistId)

  // Redirect to onboarding if no watchlists
  useEffect(() => {
    if (!wlLoading && watchlists.length === 0) {
      navigate('/onboarding')
    }
  }, [wlLoading, watchlists, navigate])

  const greeting = getGreeting()
  const firstName = user?.full_name?.split(' ')[0] || user?.email?.split('@')[0] || 'there'

  return (
    <AppLayout>
      <div className="flex gap-8">
        {/* Sidebar */}
        <aside className="hidden lg:block w-52 flex-shrink-0">
          <div className="sticky top-24 bg-surface-card border border-surface-border rounded-xl p-4">
            <WatchlistSidebar
              watchlists={watchlists}
              activeId={activeWatchlistId}
              onSelect={setActiveWatchlistId}
              onCreate={async (name) => { await createWatchlist(name) }}
              onRename={(id, name) => updateWatchlist(id, name).then(() => {})}
              onDelete={deleteWatchlist}
            />
          </div>
        </aside>

        {/* Main */}
        <div className="flex-1 min-w-0 space-y-8 animate-fade-in">
          {/* Header */}
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold text-white">
                {greeting}, {firstName} 👋
              </h1>
              <p className="text-slate-400 mt-1">
                Here's what changed since you last checked.
              </p>
              {data?.last_checked && (
                <p className="text-xs text-slate-600 mt-1 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  Last checked {formatTimeAgo(data.last_checked)}
                </p>
              )}
            </div>
            <button
              onClick={refetch}
              className="flex items-center gap-2 px-3 py-2 text-sm text-slate-400 hover:text-white bg-surface-card border border-surface-border rounded-lg hover:border-slate-600 transition-colors flex-shrink-0"
              title="Refresh"
            >
              <RefreshCw className={clsx('w-4 h-4', loading && 'animate-spin')} />
              <span className="hidden sm:block">Refresh</span>
            </button>
          </div>

          {/* Error */}
          {error && (
            <Alert
              variant="error"
              title="Unable to fetch the latest market data"
              message={`${error}${lastFetch ? ` Showing snapshot from ${formatDate(lastFetch.toISOString())}.` : ''}`}
            />
          )}

          {loading ? (
            <DashboardSkeleton />
          ) : data ? (
            <>
              {/* Summary stats */}
              <SummaryBar data={data} />

              {/* Away banner */}
              {data.summary.days_away && data.summary.days_away >= 2 && (
                <AwayBanner days={data.summary.days_away} data={data} />
              )}

              {/* Partial results warning */}
              {data.partial_results && data.errors && data.errors.length > 0 && (
                <Alert
                  variant="warning"
                  title={`${data.errors.length} stock${data.errors.length > 1 ? 's' : ''} could not be updated`}
                  message={`${data.errors.map(e => e.ticker).join(', ')} — showing other stocks normally. ${data.errors[0]?.error ?? ''}`}
                />
              )}

              {/* First visit */}
              {data.is_first_visit && (
                <Alert
                  variant="info"
                  message="This is your first visit. We've saved today's market state as your checkpoint. Come back later to see what changed."
                />
              )}

              {/* Empty watchlist */}
              {data.summary.total === 0 && <EmptyWatchlist watchlistId={activeWatchlistId} />}

              {/* Needs Attention */}
              {data.needs_attention.length > 0 && (
                <section className="animate-slide-up">
                  <div className="flex items-center gap-2 mb-4">
                    <AlertTriangle className="w-5 h-5 text-red-500" />
                    <h2 className="text-lg font-semibold text-white">Needs Your Attention</h2>
                    <span className="px-2 py-0.5 rounded-full bg-red-900/50 text-red-300 text-xs font-semibold border border-red-800">
                      {data.needs_attention.length}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {data.needs_attention.map((item) => (
                      <AttentionCard key={item.ticker} item={item} />
                    ))}
                  </div>
                </section>
              )}

              {/* Worth Watching */}
              {data.worth_watching.length > 0 && (
                <section className="animate-slide-up">
                  <div className="flex items-center gap-2 mb-4">
                    <Activity className="w-5 h-5 text-yellow-500" />
                    <h2 className="text-lg font-semibold text-white">Worth Watching</h2>
                    <span className="px-2 py-0.5 rounded-full bg-yellow-900/50 text-yellow-300 text-xs font-semibold border border-yellow-800">
                      {data.worth_watching.length}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {data.worth_watching.map((item) => (
                      <WatchingCard key={item.ticker} item={item} />
                    ))}
                  </div>
                </section>
              )}

              {/* Normal */}
              <NormalSection items={data.normal} />
            </>
          ) : null}
        </div>
      </div>
    </AppLayout>
  )
}

function SummaryBar({ data }: { data: ReturnType<typeof useDashboard>['data'] }) {
  if (!data) return null
  const { summary } = data

  return (
    <div className="grid grid-cols-3 gap-4">
      <div className="bg-red-950/40 border border-red-900/50 rounded-xl p-4 text-center">
        <p className="text-3xl font-bold text-red-400">{summary.needs_attention_count}</p>
        <p className="text-xs text-red-500/80 mt-1 uppercase tracking-wide">Needs Attention</p>
      </div>
      <div className="bg-yellow-950/40 border border-yellow-900/50 rounded-xl p-4 text-center">
        <p className="text-3xl font-bold text-yellow-400">{summary.worth_watching_count}</p>
        <p className="text-xs text-yellow-500/80 mt-1 uppercase tracking-wide">Worth Watching</p>
      </div>
      <div className="bg-green-950/40 border border-green-900/50 rounded-xl p-4 text-center">
        <p className="text-3xl font-bold text-green-400">{summary.normal_count}</p>
        <p className="text-xs text-green-500/80 mt-1 uppercase tracking-wide">No Change</p>
      </div>
    </div>
  )
}

function AwayBanner({ days, data }: { days: number; data: NonNullable<ReturnType<typeof useDashboard>['data']> }) {
  return (
    <div className="bg-blue-950/40 border border-blue-900/50 rounded-xl p-5">
      <div className="flex items-start gap-3">
        <Calendar className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
        <div>
          <h3 className="font-semibold text-white">
            You were away for {days} {days === 1 ? 'day' : 'days'}
          </h3>
          <p className="text-sm text-slate-400 mt-1">Here's what you missed:</p>
          <div className="flex gap-4 mt-3">
            {data.summary.needs_attention_count > 0 && (
              <span className="text-sm text-red-400">🔴 {data.summary.needs_attention_count} major change{data.summary.needs_attention_count > 1 ? 's' : ''}</span>
            )}
            {data.summary.worth_watching_count > 0 && (
              <span className="text-sm text-yellow-400">🟡 {data.summary.worth_watching_count} notable change{data.summary.worth_watching_count > 1 ? 's' : ''}</span>
            )}
            {data.summary.normal_count > 0 && (
              <span className="text-sm text-green-400">🟢 {data.summary.normal_count} stable</span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function EmptyWatchlist({ watchlistId }: { watchlistId?: number }) {
  const navigate = useNavigate()
  return (
    <div className="text-center py-16 bg-surface-card border border-surface-border rounded-2xl">
      <TrendingUp className="w-12 h-12 text-slate-700 mx-auto mb-4" />
      <h3 className="text-lg font-semibold text-white mb-2">Your watchlist is empty</h3>
      <p className="text-slate-400 text-sm max-w-sm mx-auto mb-6">
        Add your first stock to start tracking meaningful market changes.
      </p>
      <button
        onClick={() => navigate('/onboarding')}
        className="inline-flex items-center gap-2 px-4 py-2.5 bg-accent hover:bg-accent-hover text-white rounded-lg text-sm font-medium transition-colors"
      >
        <Plus className="w-4 h-4" />
        Add Stocks
      </button>
    </div>
  )
}
