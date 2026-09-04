import React, { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { authApi, getErrorMessage } from '../services/api'
import type { User } from '../types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, fullName?: string) => Promise<void>
  logout: () => void
  clearError: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchMe = useCallback(async () => {
    const token = localStorage.getItem('mp_token')
    if (!token) {
      setLoading(false)
      return
    }
    try {
      const res = await authApi.me()
      setUser(res.data)
    } catch {
      localStorage.removeItem('mp_token')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchMe()
  }, [fetchMe])

  const login = async (email: string, password: string) => {
    setError(null)
    try {
      const res = await authApi.login(email, password)
      localStorage.setItem('mp_token', res.data.access_token)
      const me = await authApi.me()
      setUser(me.data)
    } catch (err) {
      setError(getErrorMessage(err))
      throw err
    }
  }

  const register = async (email: string, password: string, fullName?: string) => {
    setError(null)
    try {
      const res = await authApi.register(email, password, fullName)
      localStorage.setItem('mp_token', res.data.access_token)
      const me = await authApi.me()
      setUser(me.data)
    } catch (err) {
      setError(getErrorMessage(err))
      throw err
    }
  }

  const logout = () => {
    localStorage.removeItem('mp_token')
    setUser(null)
    setError(null)
  }

  const clearError = () => setError(null)

  return (
    <AuthContext.Provider value={{ user, loading, error, login, register, logout, clearError }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
