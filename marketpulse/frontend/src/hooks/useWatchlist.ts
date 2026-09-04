import { useState, useEffect, useCallback } from 'react'
import { watchlistApi, getErrorMessage } from '../services/api'
import type { Watchlist } from '../types'

export function useWatchlists() {
  const [watchlists, setWatchlists] = useState<Watchlist[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchWatchlists = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await watchlistApi.list()
      setWatchlists(res.data)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchWatchlists()
  }, [fetchWatchlists])

  const createWatchlist = async (name: string) => {
    const res = await watchlistApi.create(name)
    setWatchlists((prev) => [...prev, res.data])
    return res.data as Watchlist
  }

  const updateWatchlist = async (id: number, name: string) => {
    const res = await watchlistApi.update(id, name)
    setWatchlists((prev) => prev.map((w) => (w.id === id ? res.data : w)))
    return res.data as Watchlist
  }

  const deleteWatchlist = async (id: number) => {
    await watchlistApi.delete(id)
    setWatchlists((prev) => prev.filter((w) => w.id !== id))
  }

  const addStock = async (watchlistId: number, ticker: string) => {
    const res = await watchlistApi.addStock(watchlistId, ticker)
    setWatchlists((prev) => prev.map((w) => (w.id === watchlistId ? res.data : w)))
    return res.data as Watchlist
  }

  const removeStock = async (watchlistId: number, ticker: string) => {
    const res = await watchlistApi.removeStock(watchlistId, ticker)
    setWatchlists((prev) => prev.map((w) => (w.id === watchlistId ? res.data : w)))
    return res.data as Watchlist
  }

  return {
    watchlists,
    loading,
    error,
    refetch: fetchWatchlists,
    createWatchlist,
    updateWatchlist,
    deleteWatchlist,
    addStock,
    removeStock,
  }
}
