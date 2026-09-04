import { clsx } from 'clsx'
import { AlertCircle, AlertTriangle, CheckCircle, Info, X } from 'lucide-react'

interface AlertProps {
  variant?: 'error' | 'warning' | 'success' | 'info'
  title?: string
  message: string
  onDismiss?: () => void
  className?: string
}

const icons = {
  error: AlertCircle,
  warning: AlertTriangle,
  success: CheckCircle,
  info: Info,
}

const styles = {
  error: 'bg-red-950/60 border-red-800 text-red-300',
  warning: 'bg-yellow-950/60 border-yellow-800 text-yellow-300',
  success: 'bg-green-950/60 border-green-800 text-green-300',
  info: 'bg-blue-950/60 border-blue-800 text-blue-300',
}

export function Alert({ variant = 'error', title, message, onDismiss, className }: AlertProps) {
  const Icon = icons[variant]

  return (
    <div className={clsx(
      'flex items-start gap-3 p-4 rounded-lg border',
      styles[variant],
      className
    )}>
      <Icon className="w-5 h-5 mt-0.5 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        {title && <p className="font-medium text-sm mb-0.5">{title}</p>}
        <p className="text-sm opacity-90">{message}</p>
      </div>
      {onDismiss && (
        <button onClick={onDismiss} className="opacity-60 hover:opacity-100 transition-opacity">
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  )
}

export function StaleDataAlert({ lastUpdated, className }: { lastUpdated: string, className?: string }) {
  const date = new Date(lastUpdated)
  const diffMins = Math.floor((Date.now() - date.getTime()) / 60000)

  if (diffMins < 5) return null

  return (
    <Alert
      variant="warning"
      message={`Data delayed — last updated ${diffMins} minutes ago. Showing latest available snapshot.`}
      className={className}
    />
  )
}
