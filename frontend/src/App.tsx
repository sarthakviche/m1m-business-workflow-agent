import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AppProvider } from './context/AppContext'
import AppShell from './components/AppShell'
import Dashboard from './pages/Dashboard'
import Chat from './pages/Chat'
import Documents from './pages/Documents'
import Customers from './pages/Customers'
import Inventory from './pages/Inventory'
import Settings from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <AppProvider>
        <AppShell>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/onboard" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/documents" element={<Documents />} />
            <Route path="/customers" element={<Customers />} />
            <Route path="/inventory" element={<Inventory />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </AppShell>
      </AppProvider>
    </BrowserRouter>
  )
}
