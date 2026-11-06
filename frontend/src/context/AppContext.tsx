import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { api, ApiError } from '../api/client'
import type { BusinessProfile, BusinessProfileUpdate } from '../api/client'
import { supabase } from '../lib/supabase'

/** `recovery`: arrived from a password-reset email and needs to choose a new password. */
export type AppStatus = 'loading' | 'signed_out' | 'recovery' | 'ready' | 'error'

interface AppContextType {
  status: AppStatus
  /** Why loading failed, when status is `error`. */
  loadError: string | null
  retry: () => void
  email: string | null
  /** Business profile from the backend; null for a new login that hasn't set one up. */
  business: BusinessProfile | null
  onboarded: boolean
  completeOnboarding: () => Promise<void>
  /** Creates the business on first save, then updates it. Every screen sees the change. */
  saveBusiness: (changes: BusinessProfileUpdate) => Promise<BusinessProfile>
  signOut: () => Promise<void>
  finishPasswordRecovery: () => void
}

const AppContext = createContext<AppContextType | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AppStatus>('loading')
  const [loadError, setLoadError] = useState<string | null>(null)
  const [email, setEmail] = useState<string | null>(null)
  const [business, setBusiness] = useState<BusinessProfile | null>(null)
  const loadedUserId = useRef<string | null>(null)

  const load = useCallback(async () => {
    setStatus('loading')
    setLoadError(null)
    try {
      const me = await api.me()
      setEmail(me.email)
      setBusiness(me.business)
      setStatus('ready')
    } catch (err) {
      // An expired session means signing in again, not a screen with a retry button.
      if (supabase && err instanceof ApiError && err.status === 401) {
        loadedUserId.current = null
        setStatus('signed_out')
        return
      }
      setLoadError(err instanceof Error ? err.message : 'Could not load your account.')
      setStatus('error')
    }
  }, [])

  useEffect(() => {
    if (!supabase) {
      void load()
      return
    }
    const { data } = supabase.auth.onAuthStateChange((event, session) => {
      // Supabase holds a lock during this callback, and calling back into it (as
      // api.me does) would deadlock. setTimeout lets the callback finish first.
      setTimeout(() => {
        if (event === 'PASSWORD_RECOVERY') {
          loadedUserId.current = session?.user.id ?? null
          setStatus('recovery')
        } else if (!session) {
          loadedUserId.current = null
          setEmail(null)
          setBusiness(null)
          setStatus('signed_out')
        } else if (session.user.id !== loadedUserId.current) {
          // Also fires on token refreshes and tab switches, which need no reload.
          loadedUserId.current = session.user.id
          void load()
        }
      }, 0)
    })
    return () => data.subscription.unsubscribe()
  }, [load])

  async function saveBusiness(changes: BusinessProfileUpdate) {
    const updated = business ? await api.updateBusiness(changes) : await api.createBusiness(changes)
    setBusiness(updated)
    return updated
  }

  async function completeOnboarding() {
    setBusiness(await api.completeOnboarding())
  }

  async function signOut() {
    await supabase?.auth.signOut()
  }

  function finishPasswordRecovery() {
    void load()
  }

  return (
    <AppContext.Provider value={{
      status, loadError, retry: () => void load(), email, business,
      onboarded: business?.onboarded ?? false,
      completeOnboarding, saveBusiness, signOut, finishPasswordRecovery,
    }}>
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const c = useContext(AppContext)
  if (!c) throw new Error('useApp must be used within AppProvider')
  return c
}
