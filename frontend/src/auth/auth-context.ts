import { createContext } from 'react'

import type { Session, User } from '../types'

export interface AuthValue {
  session: Session | null
  user: User | null
  token: string
  checking: boolean
  signIn: (email: string, password: string) => Promise<void>
  signOut: () => Promise<void>
}

export const AuthContext = createContext<AuthValue | null>(null)
