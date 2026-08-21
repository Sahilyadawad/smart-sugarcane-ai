import { useEffect, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  Bot,
  Droplets,
  FlaskConical,
  History,
  LayoutDashboard,
  Leaf,
  LogOut,
  Menu,
  Mountain,
  Settings,
  Sprout,
  X,
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { Logo, ThemeToggle } from './PublicLayout'

const NAV = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/irrigation', label: 'Smart Irrigation', icon: Droplets },
  { to: '/plant-analysis', label: 'Plant Health', icon: Leaf },
  { to: '/soil-analysis', label: 'Soil Analysis', icon: Mountain },
  { to: '/varieties', label: 'Variety Guide', icon: Sprout },
  { to: '/fertilizer', label: 'Fertilizer', icon: FlaskConical },
  { to: '/assistant', label: 'AI Assistant', icon: Bot },
  { to: '/history', label: 'History', icon: History },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export default function DashboardLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [open, setOpen] = useState(false)

  // Close the mobile drawer whenever the route changes.
  useEffect(() => setOpen(false), [location.pathname])

  const handleLogout = () => {
    logout()
    navigate('/', { replace: true })
  }

  const initials = (user?.name ?? '?')
    .split(' ')
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('')

  const sidebar = (
    <div className="flex h-full flex-col">
      <div className="flex h-16 shrink-0 items-center justify-between px-5">
        <Logo />
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="grid size-9 place-items-center rounded-xl text-slate-500 lg:hidden"
          aria-label="Close menu"
        >
          <X className="size-5" />
        </button>
      </div>

      <nav className="scrollbar-thin flex-1 space-y-1 overflow-y-auto px-3 py-4">
        {NAV.map((item) => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                  isActive
                    ? 'bg-cane-600 text-white shadow-sm'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-white'
                }`
              }
            >
              <Icon className="size-[18px] shrink-0" />
              {item.label}
            </NavLink>
          )
        })}
      </nav>

      <div className="shrink-0 border-t border-slate-200 p-3 dark:border-slate-800">
        <div className="flex items-center gap-3 rounded-xl px-2 py-2">
          <span className="grid size-9 shrink-0 place-items-center rounded-full bg-cane-100 text-sm font-bold text-cane-800 dark:bg-cane-900 dark:text-cane-200">
            {initials}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-slate-800 dark:text-slate-200">
              {user?.name}
            </p>
            <p className="truncate text-xs text-slate-500 dark:text-slate-400">{user?.email}</p>
          </div>
        </div>
        <button type="button" onClick={handleLogout} className="btn-ghost mt-1 w-full justify-start">
          <LogOut className="size-4" />
          Sign out
        </button>
      </div>
    </div>
  )

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-slate-200 bg-white lg:block dark:border-slate-800 dark:bg-slate-900">
        {sidebar}
      </aside>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm"
            onClick={() => setOpen(false)}
            aria-label="Close menu overlay"
          />
          <aside className="absolute inset-y-0 left-0 w-72 border-r border-slate-200 bg-white shadow-xl dark:border-slate-800 dark:bg-slate-900">
            {sidebar}
          </aside>
        </div>
      )}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-slate-200 bg-white/85 px-4 backdrop-blur-lg sm:px-6 dark:border-slate-800 dark:bg-slate-900/85">
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="grid size-9 place-items-center rounded-xl text-slate-600 lg:hidden dark:text-slate-300"
            aria-label="Open menu"
          >
            <Menu className="size-5" />
          </button>
          <h1 className="flex-1 truncate font-display text-lg font-bold">
            {NAV.find((item) => item.to === location.pathname)?.label ?? 'Smart Sugarcane AI'}
          </h1>
          <ThemeToggle />
        </header>

        <main className="p-4 sm:p-6 lg:p-8">
          <div className="mx-auto max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
