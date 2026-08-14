import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

// Pages — stubs for Phase 7 implementation
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Chat from './pages/Chat'
import Documents from './pages/Documents'
import Customers from './pages/Customers'
import Inventory from './pages/Inventory'
import Settings from './pages/Settings'
import BusinessProfile from './pages/Onboarding/BusinessProfile'
import CatalogChoice from './pages/Onboarding/CatalogChoice'
import ManualItemEntry from './pages/Onboarding/ManualItemEntry'
import BulkUpload from './pages/Onboarding/BulkUpload'
import OnboardingComplete from './pages/Onboarding/OnboardingComplete'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/onboarding/profile" element={<BusinessProfile />} />
        <Route path="/onboarding/catalog" element={<CatalogChoice />} />
        <Route path="/onboarding/manual" element={<ManualItemEntry />} />
        <Route path="/onboarding/upload" element={<BulkUpload />} />
        <Route path="/onboarding/complete" element={<OnboardingComplete />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/customers" element={<Customers />} />
        <Route path="/inventory" element={<Inventory />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
