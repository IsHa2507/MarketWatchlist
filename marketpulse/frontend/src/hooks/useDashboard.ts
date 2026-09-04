import { useState, useEffect, useCallback } from 'react'
import { dashboardApi, getErrorMessage } from '../services/api'
import type { DashboardResponse } from '../types'

export function useDashboard(watchlistId?: number) {
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastFetch, setLastFetch] = useState<Date | null>(null)

  const fetchDashboard = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await dashboardApi.get(watchlistId)
      setData(res.data)
      setLastFetch(new Date())
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }, [watchlistId])

  useEffect(() => {
    fetchDashboard()
  }, [fetchDashboard])

  return { data, loading, error, refetch: fetchDashboard, lastFetch }
}
