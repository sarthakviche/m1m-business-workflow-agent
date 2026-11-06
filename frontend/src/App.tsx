import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AppProvider, useApp } from './context/AppContext'
import AppShell from './components/AppShell'
import { LogoMark } from './components/Logo'
import { ErrorState } from './components/ui'
import Dashboard from './pages/Dashboard'
import Chat from './pages/Chat'
import Documents from './pages/Documents'
import Customers from './pages/Customers'
import ImportCatalog from './pages/ImportCatalog'
import Inventory from './pages/Inventory'
import Login, { SetNewPassword } from './pages/Login'
import Settings from './pages/Settings'

function Splash() {
  // The free server sleeps when idle and takes up to a minute to wake, so say so.
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), 5000)
    return () => clearTimeout(timer)
  }, [])

  return (
    <main className="flex min-h-dvh flex-col items-center justify-center bg-slate-50 px-6 text-center" aria-busy="true">
      <LogoMark className="h-14 motion-safe:animate-pulse" label="Munim.ai" />
      <p className="mt-4 text-sm text-slate-500" role="status">
        {slow ? 'Waking up the server. This can take up to a minute…' : 'Loading…'}
      </p>
    </main>
  )
}

function Screens() {
  const { status, loadError, retry, business } = useApp()

  if (status === 'loading') return <Splash />
  if (status === 'signed_out') return <Login />
  if (status === 'recovery') return <SetNewPassword />
  if (status === 'error') {
    return <main className="flex min-h-dvh items-center justify-center bg-slate-50"><ErrorState message={loadError ?? 'Please try again.'} onRetry={retry} /></main>
  }

  return (
    <AppShell>
      {/* A new login has no business yet: setup appears over the shell, and screens load once it exists. */}
      {business && (
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/onboard" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/documents" element={<Documents />} />
          <Route path="/customers" element={<Customers />} />
          <Route path="/inventory" element={<Inventory />} />
          <Route path="/inventory/import" element={<ImportCatalog />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      )}
    </AppShell>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <Screens />
      </AppProvider>
    </BrowserRouter>
  )
}
