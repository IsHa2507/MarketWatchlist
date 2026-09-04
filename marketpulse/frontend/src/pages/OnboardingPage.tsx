import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { TrendingUp, Search, Plus, Check, ArrowRight, X } from 'lucide-react'
import { stockApi, getErrorMessage } from '../services/api'
import { useWatchlists } from '../hooks/useWatchlist'
import type { StockSearchResult } from '../types'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Alert } from '../components/ui/Alert'
import { formatPercent } from '../utils/format'
import { clsx } from 'clsx'

const DEMO_TICKERS = ['TCS', 'NVDA', 'RELIANCE', 'INFY', 'HDFCBANK', 'AAPL', 'TSLA', 'MSFT', 'AMZN', 'ICICIBANK']

export function OnboardingPage() {
  const navigate = useNavigate()
  const { createWatchlist, addStock } = useWatchlists()
  const [step, setStep] = useState<'name' | 'stocks'>('name')
  const [watchlistName, setWatchlistName] = useState('My Portfolio')
  const [watchlistId, setWatchlistId] = useState<number | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<StockSearchResult[]>([])
  const [addedTickers, setAddedTickers] = useState<Set<string>>(new Set())
  const [searching, setSearching] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleCreateWatchlist = async () => {
    setLoading(true)
    setError(null)
    try {
      const wl = await createWatchlist(watchlistName.trim() || 'My Portfolio')
      setWatchlistId(wl.id)
      setStep('stocks')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = async (q: string) => {
    setSearchQuery(q)
    if (q.trim().length < 1) { setSearchResults([]); return }
    setSearching(true)
    try {
      const res = await stockApi.search(q.trim())
      setSearchResults(res.data.results || [])
    } catch {
      setSearchResults([])
    } finally {
      setSearching(false)
    }
  }

  const handleAddStock = async (ticker: string) => {
    if (!watchlistId || addedTickers.has(ticker)) return
    setError(null)
    try {
      await addStock(watchlistId, ticker)
      setAddedTickers((prev) => new Set([...prev, ticker]))
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const handleFinish = () => navigate('/dashboard')

  return (
    <div className="min-h-screen bg-surface flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-lg space-y-6">
        {/* Logo */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-accent rounded-xl mb-3">
            <TrendingUp className="w-6 h-6 text-white" />
          </div>
          <p className="text-slate-400 text-sm">
            {step === 'name' ? 'Step 1 of 2 — Name your watchlist' : 'Step 2 of 2 — Add stocks'}
          </p>
          <div className="flex gap-2 justify-center mt-3">
            {[0, 1].map((i) => (
              <div key={i} className={clsx('h-1.5 w-16 rounded-full transition-colors', i < (step === 'name' ? 1 : 2) ? 'bg-accent' : 'bg-surface-border')} />
            ))}
          </div>
        </div>

        {error && <Alert message={error} onDismiss={() => setError(null)} />}

        {step === 'name' && (
          <div className="bg-surface-card border border-surface-border rounded-2xl p-8 space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-white">Name your watchlist</h2>
              <p className="text-sm text-slate-400 mt-1">You can create more watchlists later</p>
            </div>
            <Input
              label="Watchlist name"
              value={watchlistName}
              onChange={(e) => setWatchlistName(e.target.value)}
              placeholder="My Portfolio"
              autoFocus
            />
            <Button onClick={handleCreateWatchlist} loading={loading} fullWidth size="lg">
              Continue <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        )}

        {step === 'stocks' && (
          <div className="bg-surface-card border border-surface-border rounded-2xl p-8 space-y-6">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-xl font-semibold text-white">Add stocks to track</h2>
                <p className="text-sm text-slate-400 mt-1">
                  {addedTickers.size === 0 ? 'Add at least one stock' : `${addedTickers.size} stock${addedTickers.size > 1 ? 's' : ''} added`}
                </p>
              </div>
              {addedTickers.size > 0 && (
                <button
                  onClick={handleFinish}
                  className="flex items-center gap-1.5 text-sm text-accent hover:text-accent-hover font-medium"
                >
                  Done <ArrowRight className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                placeholder="Search by ticker or company name"
                className="w-full bg-surface-elevated border border-surface-border rounded-lg pl-10 pr-3 py-2.5 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </div>

            {/* Search results */}
            {searchResults.length > 0 && (
              <ul className="space-y-1">
                {searchResults.map((r) => (
                  <SearchResultRow
                    key={r.ticker}
                    result={r}
                    added={addedTickers.has(r.ticker)}
                    onAdd={() => handleAddStock(r.ticker)}
                  />
                ))}
              </ul>
            )}

            {/* Quick add popular */}
            {searchResults.length === 0 && (
              <div>
                <p className="text-xs text-slate-500 mb-3 uppercase tracking-wider">Popular stocks</p>
                <div className="grid grid-cols-2 gap-2">
                  {DEMO_TICKERS.map((ticker) => (
                    <button
                      key={ticker}
                      onClick={() => handleAddStock(ticker)}
                      className={clsx(
                        'flex items-center justify-between px-3 py-2 rounded-lg border text-sm transition-all',
                        addedTickers.has(ticker)
                          ? 'bg-accent/10 border-accent/30 text-accent cursor-default'
                          : 'bg-surface-elevated border-surface-border text-slate-300 hover:border-accent/50 hover:text-white'
                      )}
                    >
                      <span className="font-medium">{ticker}</span>
                      {addedTickers.has(ticker) ? (
                        <Check className="w-3.5 h-3.5" />
                      ) : (
                        <Plus className="w-3.5 h-3.5 text-slate-500" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <Button
              onClick={handleFinish}
              fullWidth
              size="lg"
              disabled={addedTickers.size === 0}
            >
              Go to Dashboard <ArrowRight className="w-4 h-4" />
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}

function SearchResultRow({
  result,
  added,
  onAdd,
}: {
  result: StockSearchResult
  added: boolean
  onAdd: () => void
}) {
  return (
    <li className={clsx(
      'flex items-center justify-between px-3 py-2.5 rounded-lg border transition-colors',
      added ? 'bg-accent/10 border-accent/30' : 'bg-surface-elevated border-surface-border hover:border-slate-600'
    )}>
      <div>
        <span className="font-semibold text-sm text-white">{result.ticker}</span>
        <span className="ml-2 text-xs text-slate-400">{result.company_name}</span>
      </div>
      <div className="flex items-center gap-3">
        <span className={clsx('text-xs font-medium', result.price_change_percent >= 0 ? 'text-green-400' : 'text-red-400')}>
          {formatPercent(result.price_change_percent)}
        </span>
        <button
          onClick={onAdd}
          disabled={added}
          className={clsx(
            'p-1.5 rounded-md transition-colors',
            added ? 'text-accent cursor-default' : 'text-slate-500 hover:text-white hover:bg-surface-border'
          )}
        >
          {added ? <Check className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
        </button>
      </div>
    </li>
  )
}
