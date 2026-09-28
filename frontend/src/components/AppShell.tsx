import { useEffect, useRef, useState, ReactNode } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import OnboardOverlay from './OnboardOverlay'

// ── SVG Icons ─────────────────────────────────────────────────────────────────

function IconHome({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill={active ? '#f97316' : 'none'}
      stroke={active ? '#f97316' : 'currentColor'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5z" />
      <polyline points="9 21 9 12 15 12 15 21" />
    </svg>
  )
}

function IconChat({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill={active ? '#f97316' : 'none'}
      stroke={active ? '#f97316' : 'currentColor'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  )
}

function IconDoc({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill={active ? '#f97316' : 'none'}
      stroke={active ? '#f97316' : 'currentColor'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10 9 9 9 8 9" />
    </svg>
  )
}

function IconPeople({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill={active ? '#f97316' : 'none'}
      stroke={active ? '#f97316' : 'currentColor'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  )
}

function IconBox({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill={active ? '#f97316' : 'none'}
      stroke={active ? '#f97316' : 'currentColor'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z" />
      <polyline points="3.27 6.96 12 12.01 20.73 6.96" />
      <line x1="12" y1="22.08" x2="12" y2="12" />
    </svg>
  )
}

function IconGear({ active }: { active: boolean }) {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill={active ? '#f97316' : 'none'}
      stroke={active ? '#f97316' : 'currentColor'} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  )
}

// ── Nav items ──────────────────────────────────────────────────────────────────

interface NavItem {
  path: string
  label: string
  Icon: React.FC<{ active: boolean }>
}

const NAV: NavItem[] = [
  { path: '/dashboard',  label: 'Home',      Icon: IconHome   },
  { path: '/chat',       label: 'Chat',      Icon: IconChat   },
  { path: '/documents',  label: 'Docs',      Icon: IconDoc    },
  { path: '/customers',  label: 'Customers', Icon: IconPeople },
  { path: '/inventory',  label: 'Inventory', Icon: IconBox    },
  { path: '/settings',   label: 'Settings',  Icon: IconGear   },
]

const MOBILE_NAV = NAV.slice(0, 5) // Home, Chat, Docs, Customers, Inventory

// ── Logo ───────────────────────────────────────────────────────────────────────

function Logo({ collapsed }: { collapsed: boolean }) {
  return (
    <div className={`flex items-center gap-2.5 px-3 py-2 ${collapsed ? 'justify-center' : ''}`}>
      <div className="flex-shrink-0 w-9 h-9 rounded-full bg-gradient-to-br from-orange-500 to-orange-600 flex items-center justify-center shadow-md shadow-orange-200">
        <span className="text-white font-extrabold text-base leading-none">M</span>
      </div>
      {!collapsed && (
        <span className="font-display font-bold text-slate-900 text-lg tracking-tight whitespace-nowrap">
          Munim.ai
        </span>
      )}
    </div>
  )
}

// ── User avatar (bottom of sidebar) ───────────────────────────────────────────

function UserAvatar({ collapsed }: { collapsed: boolean }) {
  return (
    <div className={`flex items-center gap-2.5 px-3 py-2 ${collapsed ? 'justify-center' : ''}`}>
      <div className="flex-shrink-0 w-9 h-9 rounded-full bg-slate-200 flex items-center justify-center overflow-hidden">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
          <circle cx="12" cy="7" r="4" />
        </svg>
      </div>
      {!collapsed && (
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-900 truncate">Account</p>
          <p className="text-xs text-slate-400 truncate">Free plan</p>
        </div>
      )}
    </div>
  )
}

// ── AppShell ───────────────────────────────────────────────────────────────────

interface AppShellProps {
  children: ReactNode
}

export default function AppShell({ children }: AppShellProps) {
  const { onboarded, completeOnboarding } = useApp()
  const location = useLocation()
  const navigate = useNavigate()
  const activeRef = useRef<HTMLButtonElement>(null)

  // Collapse sidebar to icon-only below xl
  const [sidebarExpanded, setSidebarExpanded] = useState(window.innerWidth >= 1280)

  useEffect(() => {
    const handleResize = () => setSidebarExpanded(window.innerWidth >= 1280)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  function isActive(path: string) {
    return location.pathname === path || location.pathname.startsWith(path + '/')
  }

  function handleNav(path: string) {
    navigate(path)
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-50">
      {/* ── Desktop Sidebar ── */}
      <aside
        className={`hidden md:flex flex-col bg-white border-r border-slate-100 shadow-sm flex-shrink-0 transition-all duration-200
          ${sidebarExpanded ? 'w-56' : 'w-16'}`}
      >
        {/* Logo */}
        <div className="pt-5 pb-4 px-2 border-b border-slate-50">
          <Logo collapsed={!sidebarExpanded} />
        </div>

        {/* Nav links */}
        <nav className="flex-1 py-4 px-2 flex flex-col gap-1 overflow-y-auto">
          {NAV.map(({ path, label, Icon }) => {
            const active = isActive(path)
            return (
              <button
                key={path}
                ref={active ? activeRef : undefined}
                onClick={() => handleNav(path)}
                className={`flex items-center gap-3 w-full rounded-xl px-3 py-2.5 text-sm font-medium transition-all
                  ${sidebarExpanded ? '' : 'justify-center'}
                  ${active
                    ? 'bg-orange-50 text-orange-600 font-semibold'
                    : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900'
                  }`}
                title={!sidebarExpanded ? label : undefined}
              >
                <span className="flex-shrink-0"><Icon active={active} /></span>
                {sidebarExpanded && <span className="truncate">{label}</span>}
              </button>
            )
          })}
        </nav>

        {/* User avatar */}
        <div className="border-t border-slate-50 py-3 px-2">
          <UserAvatar collapsed={!sidebarExpanded} />
        </div>
      </aside>

      {/* ── Main content ── */}
      <main className="flex-1 min-h-0 overflow-auto bg-slate-50 pb-20 md:pb-0">
        {children}
      </main>

      {/* ── Mobile Bottom Tab Bar ── */}
      <nav className="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-100 shadow-lg z-40 flex md:hidden pb-4">
        {MOBILE_NAV.map(({ path, label, Icon }) => {
          const active = isActive(path)
          return (
            <button
              key={path}
              onClick={() => handleNav(path)}
              className="flex-1 flex flex-col items-center justify-center pt-3 pb-1 gap-0.5"
            >
              <Icon active={active} />
              <span className={`text-[10px] font-medium ${active ? 'text-orange-500' : 'text-slate-400'}`}>
                {label}
              </span>
            </button>
          )
        })}
      </nav>

      {/* ── Onboarding overlay ── */}
      {!onboarded && (
        <OnboardOverlay onComplete={completeOnboarding} />
      )}
    </div>
  )
}
