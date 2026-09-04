import axios, { AxiosError } from 'axios'

const BASE_URL = (import.meta.env.VITE_API_URL as string) || 'http://localhost:8000'

export const api = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT automatically
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('mp_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle auth errors globally
api.interceptors.response.use(
  (res) => res,
  (err: AxiosError) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('mp_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ── Auth ──────────────────────────────────────────────────────────────────────

export const authApi = {
  register: (email: string, password: string, full_name?: string) =>
    api.post('/auth/register', { email, password, full_name }),

  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),

  me: () => api.get('/auth/me'),
}

// ── Watchlists ────────────────────────────────────────────────────────────────

export const watchlistApi = {
  list: () => api.get('/watchlists'),
  create: (name: string) => api.post('/watchlists', { name }),
  update: (id: number, name: string) => api.put(`/watchlists/${id}`, { name }),
  delete: (id: number) => api.delete(`/watchlists/${id}`),
  addStock: (id: number, ticker: string) =>
    api.post(`/watchlists/${id}/stocks`, { ticker }),
  removeStock: (id: number, ticker: string) =>
    api.delete(`/watchlists/${id}/stocks/${ticker}`),
}

// ── Stocks ────────────────────────────────────────────────────────────────────

export const stockApi = {
  search: (q: string) => api.get('/stocks/search', { params: { q } }),
  get: (ticker: string) => api.get(`/stocks/${ticker}`),
  history: (ticker: string, days = 30) =>
    api.get(`/stocks/${ticker}/history`, { params: { days } }),
  events: (ticker: string) => api.get(`/stocks/${ticker}/events`),
}

// ── Dashboard ─────────────────────────────────────────────────────────────────

export const dashboardApi = {
  get: (watchlistId?: number) =>
    api.get('/dashboard', { params: watchlistId ? { watchlist_id: watchlistId } : {} }),
  changes: (watchlistId?: number) =>
    api.get('/dashboard/changes', { params: watchlistId ? { watchlist_id: watchlistId } : {} }),
  attention: (watchlistId?: number) =>
    api.get('/dashboard/attention', { params: watchlistId ? { watchlist_id: watchlistId } : {} }),
}

// ── Error helpers ─────────────────────────────────────────────────────────────

export function getErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((d: { msg: string }) => d.msg).join(', ')
    if (err.code === 'ERR_NETWORK') return 'Unable to reach the server. Check your connection.'
    if (err.code === 'ECONNABORTED') return 'Request timed out. Please try again.'
    return err.message
  }
  if (err instanceof Error) return err.message
  return 'An unexpected error occurred.'
}
