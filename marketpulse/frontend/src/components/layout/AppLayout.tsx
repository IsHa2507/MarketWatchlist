import { useState, useRef, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { Search, Bell, LogOut, User, TrendingUp, ChevronDown, X, Plus } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import { stockApi, getErrorMessage } from '../../services/api'
import type { StockSearchResult } from '../../types'
import { formatPercent } from '../../utils/format'
import { clsx } from 'clsx'

interface AppLayoutProps {
  children: React.ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<StockSearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [showSearch, setShowSearch] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const searchRef = useRef<HTMLDivElement>(null)
  const searchTimeout = useRef<ReturnType<typeof setTimeout>>()

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowSearch(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSearch = (q: string) => {
    setSearchQuery(q)
    clearTimeout(searchTimeout.current)
    if (q.trim().length < 1) {
      setSearchResults([])
      setShowSearch(false)
      return
    }
    searchTimeout.current = setTimeout(async () => {
      setSearching(true)
      setShowSearch(true)
      try {
        const res = await stockApi.search(q.trim())
        setSearchResults(res.data.results || [])
      } catch {
        setSearchResults([])
      } finally {
        setSearching(false)
      }
    }, 300)
  }

  const handleSelectStock = (ticker: string) => {
    setSearchQuery('')
    setShowSearch(false)
    setSearchResults([])
    navigate(`/stocks/${ticker}`)
  }

  return (
    <div className="min-h-screen bg-surface text-slate-200">
      {/* Nav */}
      <nav className="sticky top-0 z-50 bg-surface/95 backdrop-blur border-b border-surface-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 gap-4">
            {/* Logo */}
            <Link to="/dashboard" className="flex items-center gap-2.5 flex-shrink-0">
              <div className="w-8 h-8 bg-accent rounded-lg flex items-center justify-center">
                <TrendingUp className="w-5 h-5 text-white" />
              </div>
              <span className="font-bold text-lg text-white hidden sm:block">MarketPulse</span>
            </Link>

            {/* Search */}
            <div ref={searchRef} className="relative flex-1 max-w-md">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => handleSearch(e.target.value)}
                  onFocus={() => searchQuery && setShowSearch(true)}
                  placeholder="Search stocks... (TCS, NVDA, AAPL)"
                  className="w-full bg-surface-elevated border border-surface-border rounded-lg pl-10 pr-10 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent"
                />
                {searchQuery && (
                  <button
                    onClick={() => { setSearchQuery(''); setShowSearch(false); setSearchResults([]) }}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Search dropdown */}
              {showSearch && (
                <div className="absolute top-full mt-1 w-full bg-surface-card border border-surface-border rounded-xl shadow-2xl overflow-hidden z-50">
                  {searching ? (
                    <div className="p-4 text-center text-sm text-slate-500">Searching...</div>
                  ) : searchResults.length === 0 ? (
                    <div className="p-4 text-center text-sm text-slate-500">No results for "{searchQuery}"</div>
                  ) : (
                    <ul>
                      {searchResults.map((r) => (
                        <li key={r.ticker}>
                          <button
                            onClick={() => handleSelectStock(r.ticker)}
                            className="w-full flex items-center justify-between px-4 py-3 hover:bg-surface-elevated transition-colors text-left"
                          >
                            <div>
                              <p className="font-semibold text-sm text-white">{r.ticker}</p>
                              <p className="text-xs text-slate-400">{r.company_name}</p>
                            </div>
                            <div className="text-right">
                              <p className="text-sm font-medium text-white">
                                {r.currency === 'INR' ? '₹' : '$'}{r.price.toLocaleString()}
                              </p>
                              <p className={clsx(
                                'text-xs font-medium',
                                r.price_change_percent >= 0 ? 'text-green-400' : 'text-red-400'
                              )}>
                                {formatPercent(r.price_change_percent)}
                              </p>
                            </div>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>

            {/* Right side */}
            <div className="flex items-center gap-2">
              <Link
                to="/watchlist/new"
                className="hidden sm:flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors px-3 py-2 rounded-lg hover:bg-surface-elevated"
              >
                <Plus className="w-4 h-4" />
                <span>New List</span>
              </Link>

              {/* User menu */}
              <div className="relative">
                <button
                  onClick={() => setShowUserMenu(!showUserMenu)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-surface-elevated transition-colors"
                >
                  <div className="w-7 h-7 bg-accent/20 border border-accent/30 rounded-full flex items-center justify-center">
                    <User className="w-4 h-4 text-accent" />
                  </div>
                  <span className="hidden sm:block text-sm text-slate-300 max-w-[120px] truncate">
                    {user?.full_name || user?.email?.split('@')[0]}
                  </span>
                  <ChevronDown className="w-4 h-4 text-slate-500" />
                </button>

                {showUserMenu && (
                  <div className="absolute right-0 top-full mt-1 w-52 bg-surface-card border border-surface-border rounded-xl shadow-2xl overflow-hidden z-50">
                    <div className="px-4 py-3 border-b border-surface-border">
                      <p className="text-sm font-medium text-white truncate">{user?.full_name || 'User'}</p>
                      <p className="text-xs text-slate-500 truncate">{user?.email}</p>
                    </div>
                    <Link
                      to="/dashboard"
                      onClick={() => setShowUserMenu(false)}
                      className="flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-300 hover:bg-surface-elevated hover:text-white transition-colors"
                    >
                      <TrendingUp className="w-4 h-4" />
                      Dashboard
                    </Link>
                    <button
                      onClick={() => { logout(); setShowUserMenu(false) }}
                      className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-slate-300 hover:bg-surface-elevated hover:text-white transition-colors text-left border-t border-surface-border mt-1"
                    >
                      <LogOut className="w-4 h-4" />
                      Sign out
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* Page content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>
    </div>
  )
}
