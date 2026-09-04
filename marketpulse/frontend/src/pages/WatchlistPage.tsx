import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, Plus, X, TrendingUp, TrendingDown, Check } from 'lucide-react'
import { stockApi, getErrorMessage } from '../services/api'
import { useWatchlists } from '../hooks/useWatchlist'
import { AppLayout } from '../components/layout/AppLayout'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import type { StockSearchResult, Watchlist } from '../types'
import { formatPercent } from '../utils/format'
import { clsx } from 'clsx'

export function WatchlistPage() {
  const navigate = useNavigate()
  const {
    watchlists, loading,
    createWatchlist, updateWatchlist, deleteWatchlist,
    addStock, removeStock,
  } = useWatchlists()
  const [activeId, setActiveId] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<StockSearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [newName, setNewName] = useState('')
  const [creatingList, setCreatingList] = useState(false)

  const activeWatchlist = watchlists.find((w) => w.id === activeId) || watchlists[0] || null

  const handleSearch = async (q: string) => {
    setSearchQuery(q)
    if (q.trim().length < 1) { setSearchResults([]); return }
    setSearching(true)
    try {
      const res = await stockApi.search(q.trim())
      setSearchResults(res.data.results || [])
    } catch { setSearchResults([]) }
    finally { setSearching(false) }
  }

  const handleAdd = async (ticker: string) => {
    if (!activeWatchlist) return
    setError(null)
    try {
      await addStock(activeWatchlist.id, ticker)
    } catch (err) { setError(getErrorMessage(err)) }
  }

  const handleRemove = async (ticker: string) => {
    if (!activeWatchlist) return
    try {
      await removeStock(activeWatchlist.id, ticker)
    } catch (err) { setError(getErrorMessage(err)) }
  }

  const handleCreateList = async () => {
    if (!newName.trim()) return
    try {
      const wl = await createWatchlist(newName.trim())
      setActiveId(wl.id)
      setNewName('')
      setCreatingList(false)
    } catch (err) { setError(getErrorMessage(err)) }
  }

  const handleDeleteList = async (id: number) => {
    if (!confirm('Delete this watchlist and all its stocks?')) return
    try {
      await deleteWatchlist(id)
      setActiveId(null)
    } catch (err) { setError(getErrorMessage(err)) }
  }

  return (
    <AppLayout>
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-white">Manage Watchlists</h1>
            <p className="text-slate-400 text-sm mt-1">Add, remove, and organise your tracked stocks</p>
          </div>
          <Button onClick={() => setCreatingList(true)} size="sm" variant="secondary">
            <Plus className="w-4 h-4" /> New List
          </Button>
        </div>

        {error && <Alert message={error} onDismiss={() => setError(null)} />}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left: watchlist picker */}
          <div className="space-y-2">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Your Lists</p>

            {creatingList && (
              <div className="flex gap-2 bg-surface-elevated border border-accent/40 rounded-lg p-2">
                <input
                  autoFocus
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleCreateList()}
                  placeholder="List name..."
                  className="flex-1 bg-transparent text-sm text-white placeholder-slate-500 focus:outline-none"
                />
                <button onClick={handleCreateList} className="text-green-400 hover:text-green-300">
                  <Check className="w-4 h-4" />
                </button>
                <button onClick={() => setCreatingList(false)} className="text-slate-500">
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}

            {loading ? (
              <div className="text-sm text-slate-500 py-4 text-center">Loading...</div>
            ) : watchlists.length === 0 ? (
              <p className="text-sm text-slate-600 text-center py-4">No watchlists yet</p>
            ) : watchlists.map((wl) => (
              <WatchlistListItem
                key={wl.id}
                watchlist={wl}
                active={activeWatchlist?.id === wl.id}
                onSelect={() => setActiveId(wl.id)}
                onDelete={() => handleDeleteList(wl.id)}
              />
            ))}
          </div>

          {/* Right: stocks in active watchlist + search */}
          <div className="lg:col-span-2 space-y-4">
            {activeWatchlist ? (
              <>
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold text-white">{activeWatchlist.name}</h2>
                  <span className="text-sm text-slate-500">{activeWatchlist.stocks.length} stocks</span>
                </div>

                {/* Search to add */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => handleSearch(e.target.value)}
                    placeholder="Search stocks to add..."
                    className="w-full bg-surface-elevated border border-surface-border rounded-lg pl-10 pr-3 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                </div>

                {/* Search results */}
                {searchResults.length > 0 && (
                  <div className="bg-surface-card border border-surface-border rounded-xl overflow-hidden">
                    {searchResults.map((r) => {
                      const inList = activeWatchlist.stocks.some((s) => s.ticker === r.ticker)
                      return (
                        <div
                          key={r.ticker}
                          className="flex items-center justify-between px-4 py-3 border-b border-surface-border last:border-0 hover:bg-surface-elevated transition-colors"
                        >
                          <div>
                            <button
                              onClick={() => navigate(`/stocks/${r.ticker}`)}
                              className="font-semibold text-sm text-white hover:text-accent"
                            >
                              {r.ticker}
                            </button>
                            <p className="text-xs text-slate-400">{r.company_name}</p>
                          </div>
                          <div className="flex items-center gap-3">
                            <span className={clsx('text-xs font-medium', r.price_change_percent >= 0 ? 'text-green-400' : 'text-red-400')}>
                              {formatPercent(r.price_change_percent)}
                            </span>
                            <button
                              onClick={() => inList ? handleRemove(r.ticker) : handleAdd(r.ticker)}
                              className={clsx(
                                'p-1.5 rounded-md border transition-colors text-xs font-medium',
                                inList
                                  ? 'border-red-800 text-red-400 hover:bg-red-900/30'
                                  : 'border-surface-border text-slate-400 hover:border-accent hover:text-accent'
                              )}
                            >
                              {inList ? <X className="w-3.5 h-3.5" /> : <Plus className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )}

                {/* Current stocks */}
                {activeWatchlist.stocks.length === 0 ? (
                  <div className="text-center py-12 bg-surface-card border border-surface-border rounded-xl">
                    <TrendingUp className="w-10 h-10 text-slate-700 mx-auto mb-3" />
                    <p className="text-slate-400 text-sm">No stocks yet. Search above to add some.</p>
                  </div>
                ) : (
                  <div className="bg-surface-card border border-surface-border rounded-xl overflow-hidden">
                    <div className="px-4 py-2 bg-surface-elevated border-b border-surface-border">
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Tracked Stocks</p>
                    </div>
                    {activeWatchlist.stocks.map((s) => (
                      <div
                        key={s.ticker}
                        className="flex items-center justify-between px-4 py-3 border-b border-surface-border last:border-0 hover:bg-surface-elevated group transition-colors"
                      >
                        <button
                          onClick={() => navigate(`/stocks/${s.ticker}`)}
                          className="font-medium text-sm text-white hover:text-accent transition-colors"
                        >
                          {s.ticker}
                        </button>
                        <button
                          onClick={() => handleRemove(s.ticker)}
                          className="p-1.5 text-slate-600 hover:text-red-400 hover:bg-red-900/20 rounded-md transition-colors opacity-0 group-hover:opacity-100"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div className="text-center py-16 text-slate-500 bg-surface-card border border-surface-border rounded-xl">
                <p className="text-sm">Select a watchlist or create a new one</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  )
}

function WatchlistListItem({
  watchlist, active, onSelect, onDelete,
}: {
  watchlist: Watchlist
  active: boolean
  onSelect: () => void
  onDelete: () => void
}) {
  return (
    <div
      className={clsx(
        'group flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer border transition-all',
        active
          ? 'bg-accent/10 border-accent/30 text-white'
          : 'border-surface-border text-slate-400 hover:text-white hover:bg-surface-elevated'
      )}
      onClick={onSelect}
    >
      <div>
        <p className="text-sm font-medium">{watchlist.name}</p>
        <p className="text-xs text-slate-600">{watchlist.stocks.length} stocks</p>
      </div>
      <button
        onClick={(e) => { e.stopPropagation(); onDelete() }}
        className="p-1 text-slate-600 hover:text-red-400 rounded opacity-0 group-hover:opacity-100 transition-all"
      >
        <X className="w-3.5 h-3.5" />
      </button>
    </div>
  )
}
