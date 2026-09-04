// ── Auth ─────────────────────────────────────────────────────────────────────

export interface User {
  id: number
  email: string
  full_name?: string
  created_at: string
  last_seen_at?: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

// ── Watchlist ─────────────────────────────────────────────────────────────────

export interface WatchlistStock {
  id: number
  ticker: string
  added_at: string
}

export interface Watchlist {
  id: number
  name: string
  created_at: string
  updated_at: string
  stocks: WatchlistStock[]
}

// ── Market Data ───────────────────────────────────────────────────────────────

export interface StockQuote {
  ticker: string
  company_name: string
  sector?: string
  currency?: string
  price: number
  price_change: number
  price_change_percent: number
  volume: number
  average_volume: number
  volatility: number
  sentiment_score: number
  sentiment_label: string
  last_updated: string
  data_confidence: string
  demo_mode?: boolean
}

export interface HistoryDataPoint {
  date: string
  timestamp: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  is_checkpoint?: boolean
}

export interface MarketEvent {
  id: number
  ticker: string
  event_type: string
  title: string
  description?: string
  sentiment: string
  impact_score: number
  source?: string
  timestamp: string
}

export interface StockSearchResult {
  ticker: string
  company_name: string
  price: number
  price_change_percent: number
  sector?: string
  currency?: string
}

// ── Attention / Dashboard ─────────────────────────────────────────────────────

export type Classification = 'CRITICAL' | 'IMPORTANT' | 'WORTH_WATCHING' | 'NORMAL'

export interface AttentionComponents {
  price: number
  volume: number
  sentiment: number
  volatility: number
  technical: number
}

export interface AttentionScore {
  ticker: string
  company_name: string
  current_price: number
  checkpoint_price?: number
  price_change_percent: number
  volume_multiplier: number
  sentiment_change: string
  sentiment_label: string
  attention_score: number
  classification: Classification
  components: AttentionComponents
  key_reasons: string[]
  explanation: string
  since?: string
  is_first_visit?: boolean
  stock_data?: StockQuote
}

export interface DashboardSummary {
  total: number
  needs_attention_count: number
  worth_watching_count: number
  normal_count: number
  days_away?: number
  watchlist_name?: string
  watchlist_id?: number
}

export interface DashboardResponse {
  needs_attention: AttentionScore[]
  worth_watching: AttentionScore[]
  normal: AttentionScore[]
  summary: DashboardSummary
  last_checked?: string
  is_first_visit: boolean
}
