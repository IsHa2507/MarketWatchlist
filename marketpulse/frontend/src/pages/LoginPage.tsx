import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { TrendingUp, Mail, Lock } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Alert } from '../components/ui/Alert'

export function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const { login, error, clearError } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()
    setLoading(true)
    try {
      await login(email, password)
      navigate('/dashboard')
    } catch {
      // error shown via context
    } finally {
      setLoading(false)
    }
  }

  // Demo login helper
  const fillDemo = () => {
    setEmail('demo@marketpulse.app')
    setPassword('demo123')
  }

  return (
    <div className="min-h-screen bg-surface flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md space-y-8">
        {/* Logo */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-accent rounded-2xl mb-4">
            <TrendingUp className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white">MarketPulse</h1>
          <p className="mt-2 text-slate-400">Watch less. Understand more.</p>
        </div>

        {/* Card */}
        <div className="bg-surface-card border border-surface-border rounded-2xl p-8 space-y-6">
          <div>
            <h2 className="text-xl font-semibold text-white">Welcome back</h2>
            <p className="text-sm text-slate-400 mt-1">Sign in to your account</p>
          </div>

          {error && (
            <Alert message={error} onDismiss={clearError} />
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              leftIcon={<Mail className="w-4 h-4" />}
              required
              autoFocus
            />
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              leftIcon={<Lock className="w-4 h-4" />}
              required
            />
            <Button type="submit" loading={loading} fullWidth size="lg" className="mt-2">
              Sign in
            </Button>
          </form>

          {/* Demo button */}
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-surface-border" />
            </div>
            <div className="relative flex justify-center text-xs uppercase text-slate-500">
              <span className="bg-surface-card px-2">or</span>
            </div>
          </div>

          <button
            onClick={fillDemo}
            className="w-full py-2.5 px-4 rounded-lg border border-dashed border-surface-border text-sm text-slate-400 hover:text-slate-200 hover:border-slate-600 transition-colors"
          >
            ✨ Fill demo credentials
          </button>
        </div>

        <p className="text-center text-sm text-slate-500">
          Don't have an account?{' '}
          <Link to="/register" className="text-accent hover:text-accent-hover font-medium">
            Create one
          </Link>
        </p>
      </div>
    </div>
  )
}
