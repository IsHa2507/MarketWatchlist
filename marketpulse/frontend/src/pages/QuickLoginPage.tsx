import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { TrendingUp } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export function QuickLoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()

  useEffect(() => {
    // Auto-login for demo
    const autoLogin = async () => {
      try {
        await login('demo@marketpulse.app', 'demo123')
        navigate('/dashboard')
      } catch (err) {
        console.error('Auto-login failed:', err)
        // If login fails, just navigate anyway for demo
        localStorage.setItem('mp_token', 'demo-bypass-token')
        setTimeout(() => window.location.href = '/dashboard', 100)
      }
    }
    autoLogin()
  }, [login, navigate])

  return (
    <div className="min-h-screen bg-surface flex items-center justify-center">
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-14 h-14 bg-accent rounded-2xl mb-4 animate-pulse">
          <TrendingUp className="w-8 h-8 text-white" />
        </div>
        <h1 className="text-2xl font-bold text-white mb-2">MarketPulse</h1>
        <p className="text-slate-400">Loading demo...</p>
      </div>
    </div>
  )
}
