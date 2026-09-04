import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { TrendingUp, Mail, Lock, User } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Alert } from '../components/ui/Alert'

export function RegisterPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [loading, setLoading] = useState(false)
  const { register, error, clearError } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()
    if (password.length < 6) return
    setLoading(true)
    try {
      await register(email, password, fullName || undefined)
      navigate('/onboarding')
    } catch {
      // error shown via context
    } finally {
      setLoading(false)
    }
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
            <h2 className="text-xl font-semibold text-white">Create your account</h2>
            <p className="text-sm text-slate-400 mt-1">Start tracking what actually matters</p>
          </div>

          {error && (
            <Alert message={error} onDismiss={clearError} />
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              label="Name (optional)"
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Your name"
              leftIcon={<User className="w-4 h-4" />}
              autoFocus
            />
            <Input
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              leftIcon={<Mail className="w-4 h-4" />}
              required
            />
            <Input
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Min. 6 characters"
              leftIcon={<Lock className="w-4 h-4" />}
              required
              minLength={6}
              error={password.length > 0 && password.length < 6 ? 'Password must be at least 6 characters' : undefined}
            />
            <Button type="submit" loading={loading} fullWidth size="lg" className="mt-2">
              Create account
            </Button>
          </form>

          {/* Value prop */}
          <div className="grid grid-cols-3 gap-3 pt-2">
            {[
              { emoji: '🔴', text: 'See what changed' },
              { emoji: '📊', text: 'Attention scoring' },
              { emoji: '🤖', text: 'AI explanations' },
            ].map((item) => (
              <div key={item.text} className="text-center p-3 bg-surface-elevated rounded-lg">
                <div className="text-lg mb-1">{item.emoji}</div>
                <p className="text-xs text-slate-500">{item.text}</p>
              </div>
            ))}
          </div>
        </div>

        <p className="text-center text-sm text-slate-500">
          Already have an account?{' '}
          <Link to="/login" className="text-accent hover:text-accent-hover font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
