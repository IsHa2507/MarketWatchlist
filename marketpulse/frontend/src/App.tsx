import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { LoginPage } from './pages/LoginPage'
import { RegisterPage } from './pages/RegisterPage'
import { QuickLoginPage } from './pages/QuickLoginPage'
import { OnboardingPage } from './pages/OnboardingPage'
import { DashboardPage } from './pages/DashboardPage'
import { StockDetailPage } from './pages/StockDetailPage'
import { WatchlistPage } from './pages/WatchlistPage'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          
          {/* Quick demo access - no auth needed */}
          <Route path="/onboarding" element={<OnboardingPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/stocks/:ticker" element={<StockDetailPage />} />
          <Route path="/watchlist/new" element={<WatchlistPage />} />
          <Route path="/watchlists" element={<WatchlistPage />} />

          {/* Default redirect */}
          <Route path="/" element={<QuickLoginPage />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
