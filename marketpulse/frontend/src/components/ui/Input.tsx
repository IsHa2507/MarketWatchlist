import { clsx } from 'clsx'
import type { InputHTMLAttributes } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  leftIcon?: React.ReactNode
}

export function Input({ label, error, leftIcon, className, ...props }: InputProps) {
  return (
    <div className="space-y-1.5">
      {label && (
        <label className="block text-sm font-medium text-slate-300">{label}</label>
      )}
      <div className="relative">
        {leftIcon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500">
            {leftIcon}
          </div>
        )}
        <input
          className={clsx(
            'w-full bg-surface-elevated border border-surface-border rounded-lg text-sm text-slate-200 placeholder-slate-500',
            'focus:outline-none focus:ring-2 focus:ring-accent focus:border-transparent',
            'transition-colors',
            leftIcon ? 'pl-10 pr-3 py-2.5' : 'px-3 py-2.5',
            error && 'border-red-600 focus:ring-red-500',
            className
          )}
          {...props}
        />
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  )
}
