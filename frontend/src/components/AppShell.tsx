import type { ReactNode } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { initials } from '../lib/format'
import Logo from './Logo'
import OnboardOverlay from './OnboardOverlay'
import { IconBox, IconChat, IconFile, IconHome, IconSettings, IconUsers } from './icons'

const NAV = [
  { path: '/dashboard', label: 'Home', Icon: IconHome },
  { path: '/chat', label: 'Assistant', Icon: IconChat },
  { path: '/documents', label: 'Documents', Icon: IconFile },
  { path: '/customers', label: 'Customers', Icon: IconUsers },
  { path: '/inventory', label: 'Stock', Icon: IconBox },
  { path: '/settings', label: 'Settings', Icon: IconSettings },
]

// Phones get the five daily-use screens; Settings sits in the top bar.
const MOBILE_NAV = NAV.slice(0, 5)

export default function AppShell({ children }: { children: ReactNode }) {
  const { onboarded, completeOnboarding, business } = useApp()
  const location = useLocation()
  // The assistant fills the viewport and manages its own scrolling.
  const fullBleed = location.pathname.startsWith('/chat')
  const businessName = business?.business_name ?? 'Your business'

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-slate-50 text-slate-900">
      {/* Desktop sidebar */}
      <aside className="hidden w-60 shrink-0 flex-col border-r border-slate-200/80 bg-white md:flex">
        <div className="px-5 pb-4 pt-5"><Logo /></div>
        <nav aria-label="Main" className="flex flex-1 flex-col gap-0.5 px-3 py-2">
          {NAV.map(({ path, label, Icon }) => (
            <NavLink key={path} to={path}
              className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors
                ${isActive ? 'bg-orange-50 text-orange-700' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`}>
              {({ isActive }) => (<><Icon size={20} className={isActive ? 'text-orange-600' : 'text-slate-400'} />{label}</>)}
            </NavLink>
          ))}
        </nav>
        <div className="m-3 flex items-center gap-3 rounded-xl bg-slate-50 p-3">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-xs font-bold text-slate-700 ring-1 ring-slate-200">
            {initials(businessName)}
          </span>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-slate-900">{businessName}</p>
            <p className="truncate text-xs text-slate-500">{business?.gstin ? `GSTIN ${business.gstin}` : business?.state ?? ''}</p>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        {/* Mobile top bar */}
        <header className="flex items-center justify-between border-b border-slate-200/80 bg-white px-4 py-3 md:hidden">
          <Logo />
          <NavLink to="/settings" aria-label="Settings"
            className={({ isActive }) => `rounded-xl p-2 ${isActive ? 'bg-orange-50 text-orange-600' : 'text-slate-500 hover:bg-slate-50'}`}>
            <IconSettings size={22} />
          </NavLink>
        </header>

        <main className={`min-h-0 flex-1 ${fullBleed ? 'flex flex-col overflow-hidden' : 'overflow-y-auto pb-20 md:pb-0'}`}>
          {children}
        </main>

        {/* Mobile bottom tabs */}
        <nav aria-label="Main" className={`grid grid-cols-5 border-t border-slate-200/80 bg-white pb-[env(safe-area-inset-bottom)] md:hidden
          ${fullBleed ? '' : 'fixed inset-x-0 bottom-0 z-30'}`}>
          {MOBILE_NAV.map(({ path, label, Icon }) => (
            <NavLink key={path} to={path}
              className={({ isActive }) => `flex flex-col items-center gap-0.5 py-2 text-[11px] font-medium ${isActive ? 'text-orange-600' : 'text-slate-500'}`}>
              <Icon size={22} />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>

      {!onboarded && <OnboardOverlay onComplete={completeOnboarding} />}
    </div>
  )
}
