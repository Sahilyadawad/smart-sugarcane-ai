import { useState } from 'react'
import { Link, NavLink, Outlet } from 'react-router-dom'
import { Leaf, Menu, Moon, Sun, X } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../hooks/useTheme'
import { API_BASE_URL, BACKEND_ORIGIN } from '../services/api'

const LINKS = [
  { to: '/#features', label: 'Features' },
  { to: '/#how-it-works', label: 'How it works' },
  { to: '/#benefits', label: 'Benefits' },
]

export function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <Link to="/" className="flex items-center gap-2.5">
      <span className="grid size-9 place-items-center rounded-xl bg-cane-600 text-white shadow-sm">
        <Leaf className="size-5" />
      </span>
      {!compact && (
        <span className="font-display text-lg font-extrabold tracking-tight text-slate-900 dark:text-white">
          Smart Sugarcane <span className="text-cane-600">AI</span>
        </span>
      )}
    </Link>
  )
}

export function ThemeToggle() {
  const { resolved, toggle } = useTheme()
  return (
    <button
      type="button"
      onClick={toggle}
      className="grid size-9 place-items-center rounded-xl text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
      aria-label={`Switch to ${resolved === 'dark' ? 'light' : 'dark'} theme`}
    >
      {resolved === 'dark' ? <Sun className="size-5" /> : <Moon className="size-5" />}
    </button>
  )
}

export default function PublicLayout() {
  const { isAuthenticated } = useAuth()
  const [open, setOpen] = useState(false)

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/85 backdrop-blur-lg dark:border-slate-800 dark:bg-slate-950/85">
        <nav className="section flex h-16 items-center justify-between gap-4">
          <Logo />

          <div className="hidden items-center gap-1 md:flex">
            {LINKS.map((link) => (
              <a
                key={link.to}
                href={link.to}
                className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900 dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white"
              >
                {link.label}
              </a>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <ThemeToggle />
            {isAuthenticated ? (
              <NavLink to="/dashboard" className="btn-primary hidden sm:inline-flex">
                Open dashboard
              </NavLink>
            ) : (
              <>
                <NavLink to="/login" className="btn-ghost hidden sm:inline-flex">
                  Sign in
                </NavLink>
                <NavLink to="/register" className="btn-primary hidden sm:inline-flex">
                  Get started
                </NavLink>
              </>
            )}
            <button
              type="button"
              onClick={() => setOpen((value) => !value)}
              className="grid size-9 place-items-center rounded-xl text-slate-600 md:hidden dark:text-slate-300"
              aria-label="Toggle navigation menu"
              aria-expanded={open}
            >
              {open ? <X className="size-5" /> : <Menu className="size-5" />}
            </button>
          </div>
        </nav>

        {open && (
          <div className="border-t border-slate-200 bg-white px-4 py-3 md:hidden dark:border-slate-800 dark:bg-slate-950">
            <div className="flex flex-col gap-1">
              {LINKS.map((link) => (
                <a
                  key={link.to}
                  href={link.to}
                  onClick={() => setOpen(false)}
                  className="rounded-lg px-3 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                >
                  {link.label}
                </a>
              ))}
              <div className="mt-2 flex gap-2 border-t border-slate-200 pt-3 dark:border-slate-800">
                {isAuthenticated ? (
                  <NavLink to="/dashboard" className="btn-primary flex-1" onClick={() => setOpen(false)}>
                    Dashboard
                  </NavLink>
                ) : (
                  <>
                    <NavLink to="/login" className="btn-secondary flex-1" onClick={() => setOpen(false)}>
                      Sign in
                    </NavLink>
                    <NavLink to="/register" className="btn-primary flex-1" onClick={() => setOpen(false)}>
                      Get started
                    </NavLink>
                  </>
                )}
              </div>
            </div>
          </div>
        )}
      </header>

      <main className="flex-1">
        <Outlet />
      </main>

      <footer className="border-t border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950">
        <div className="section py-10">
          <div className="flex flex-col gap-8 md:flex-row md:justify-between">
            <div className="max-w-sm">
              <Logo />
              <p className="mt-3 text-sm leading-relaxed text-slate-500 dark:text-slate-400">
                AI-assisted decision support for sugarcane farmers: irrigation scheduling, crop health,
                soil interpretation, variety selection and fertilizer timing.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-8 text-sm sm:grid-cols-3">
              <div>
                <h4 className="mb-3 text-xs font-bold uppercase tracking-wide text-slate-400">Features</h4>
                <ul className="space-y-2 text-slate-600 dark:text-slate-400">
                  <li>Smart irrigation</li>
                  <li>Disease detection</li>
                  <li>Soil analysis</li>
                  <li>Variety guidance</li>
                </ul>
              </div>
              <div>
                <h4 className="mb-3 text-xs font-bold uppercase tracking-wide text-slate-400">Project</h4>
                <ul className="space-y-2 text-slate-600 dark:text-slate-400">
                  <li>
                    <a
                      className="hover:text-cane-600"
                      href={`${BACKEND_ORIGIN}/docs`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      API documentation
                    </a>
                  </li>
                  <li>
                    <a
                      className="hover:text-cane-600"
                      href={`${API_BASE_URL}/system/status`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      AI model status
                    </a>
                  </li>
                </ul>
              </div>
              <div className="col-span-2 sm:col-span-1">
                <h4 className="mb-3 text-xs font-bold uppercase tracking-wide text-slate-400">
                  Important
                </h4>
                <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                  This platform provides decision support, not certified agricultural advice. Verify
                  disease, chemical and fertilizer decisions with a qualified agricultural officer.
                </p>
              </div>
            </div>
          </div>
          <div className="mt-8 border-t border-slate-200 pt-6 text-xs text-slate-400 dark:border-slate-800">
            Smart Sugarcane AI - AI-driven precision irrigation scheduling for sugarcane.
          </div>
        </div>
      </footer>
    </div>
  )
}
