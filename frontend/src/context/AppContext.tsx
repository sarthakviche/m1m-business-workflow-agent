import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { api } from '../api/client'
import type { BusinessProfile } from '../api/client'

interface AppContextType {
  onboarded: boolean
  completeOnboarding: () => void
  /** Business profile from the backend; null while loading or unavailable. */
  business: BusinessProfile | null
}

const AppContext = createContext<AppContextType | null>(null)

function readOnboarded(): boolean {
  try {
    return localStorage.getItem('m1m_onboarded') === 'true'
  } catch {
    return false
  }
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [onboarded, setOnboarded] = useState(readOnboarded)
  const [business, setBusiness] = useState<BusinessProfile | null>(null)

  useEffect(() => {
    api.business().then(setBusiness).catch(() => setBusiness(null))
  }, [])

  function completeOnboarding() {
    try {
      localStorage.setItem('m1m_onboarded', 'true')
    } catch {
      // Storage unavailable (private mode); onboarding just shows again next visit.
    }
    setOnboarded(true)
  }

  return (
    <AppContext.Provider value={{ onboarded, completeOnboarding, business }}>
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const c = useContext(AppContext)
  if (!c) throw new Error('useApp must be used within AppProvider')
  return c
}
