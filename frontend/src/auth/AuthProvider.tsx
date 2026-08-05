import { type ReactNode, useEffect, useMemo, useState } from 'react'

import { api, login } from '../lib/api'
import type { Session, User } from '../types'
import { AuthContext } from './auth-context'

const SESSION_KEY = 'opsforge.session'

function storedSession(): Session | null {
  try {
    const value = localStorage.getItem(SESSION_KEY)
    if (!value) return null
    const parsed = JSON.parse(value) as Session
    if (!parsed.access_token || new Date(parsed.expires_at) <= new Date()) return null
    return parsed
  } catch {
    return null
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(storedSession)
  const [checking, setChecking] = useState(() => storedSession() !== null)

  useEffect(() => {
    const restored = storedSession()
    if (!restored) return
    let active = true
    api<User>('/auth/me', { token: restored.access_token })
      .then((user) => {
        if (!active) return
        const freshSession = { ...restored, user }
        setSession(freshSession)
        localStorage.setItem(SESSION_KEY, JSON.stringify(freshSession))
      })
      .catch(() => {
        if (!active) return
        setSession(null)
        localStorage.removeItem(SESSION_KEY)
      })
      .finally(() => {
        if (active) setChecking(false)
      })
    return () => {
      active = false
    }
  }, [])

  const value = useMemo(
    () => ({
      session,
      user: session?.user ?? null,
      token: session?.access_token ?? '',
      checking,
      async signIn(email: string, password: string) {
        const nextSession = await login(email, password)
        setSession(nextSession)
        localStorage.setItem(SESSION_KEY, JSON.stringify(nextSession))
      },
      async signOut() {
        const token = session?.access_token
        try {
          if (token) await api('/auth/logout', { method: 'POST', token })
        } finally {
          setSession(null)
          localStorage.removeItem(SESSION_KEY)
        }
      },
    }),
    [checking, session],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
