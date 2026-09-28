import { createContext, useContext, useState, ReactNode } from 'react'

interface AppContextType {
  onboarded: boolean
  completeOnboarding: () => void
  businessName: string
  setBusinessName: (n: string) => void
}

const AppContext = createContext<AppContextType | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const [onboarded, setOnboarded] = useState(
    () => localStorage.getItem('m1m_onboarded') === 'true'
  )
  const [businessName, setBusinessName] = useState(
    () => localStorage.getItem('m1m_biz_name') || 'Your Business'
  )

  function completeOnboarding() {
    localStorage.setItem('m1m_onboarded', 'true')
    setOnboarded(true)
  }

  return (
    <AppContext.Provider value={{ onboarded, completeOnboarding, businessName, setBusinessName }}>
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const c = useContext(AppContext)
  if (!c) throw new Error('useApp must be used within AppProvider')
  return c
}
