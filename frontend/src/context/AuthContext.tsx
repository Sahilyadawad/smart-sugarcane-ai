import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { authApi } from '../services/endpoints'
import { setUnauthorizedHandler, tokenStore } from '../services/api'
import type { User } from '../types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  register: (payload: {
    name: string
    email: string
    password: string
    phone?: string
    farm_location?: string
  }) => Promise<void>
  logout: () => void
  setUser: (user: User) => void
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUserState] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const logout = useCallback(() => {
    tokenStore.clear()
    setUserState(null)
  }, [])

  // An expired token anywhere in the app drops us back to signed-out state.
  useEffect(() => {
    setUnauthorizedHandler(() => setUserState(null))
  }, [])

  const refresh = useCallback(async () => {
    if (!tokenStore.get()) {
      setUserState(null)
      setLoading(false)
      return
    }
    try {
      setUserState(await authApi.me())
    } catch {
      tokenStore.clear()
      setUserState(null)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const login = useCallback(async (email: string, password: string) => {
    const data = await authApi.login({ email, password })
    tokenStore.set(data.access_token)
    setUserState(data.user)
  }, [])

  const register = useCallback(
    async (payload: {
      name: string
      email: string
      password: string
      phone?: string
      farm_location?: string
    }) => {
      const data = await authApi.register(payload)
      tokenStore.set(data.access_token)
      setUserState(data.user)
    },
    [],
  )

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      login,
      register,
      logout,
      setUser: setUserState,
      refresh,
    }),
    [user, loading, login, register, logout, refresh],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside <AuthProvider>')
  }
  return context
}
