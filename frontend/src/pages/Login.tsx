import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ArrowRight, Eye, EyeOff, Leaf } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { describeError } from '../services/api'
import { authApi } from '../services/endpoints'
import { Alert, Field, Spinner } from '../components/ui'
import { ServerAddress } from '../components/ServerAddress'

export default function Login() {
  const { login } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()
  const location = useLocation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const from = (location.state as { from?: string } | null)?.from ?? '/dashboard'

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(email.trim(), password)
      toast.success('Signed in', 'Welcome back.')
      navigate(from, { replace: true })
    } catch (caught) {
      setError(describeError(caught, 'Sign in failed.'))
    } finally {
      setSubmitting(false)
    }
  }

  const handleForgot = async () => {
    if (!email.trim()) {
      toast.info('Enter your email first', 'Type your email address, then click the link again.')
      return
    }
    try {
      const response = await authApi.forgotPassword(email.trim())
      toast.info('Password reset', response.detail)
    } catch (caught) {
      toast.error('Could not process that', describeError(caught))
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Form side */}
      <div className="flex items-center justify-center px-5 py-12 sm:px-10">
        <div className="w-full max-w-md">
          <Link to="/" className="mb-8 inline-flex items-center gap-2.5">
            <span className="grid size-9 place-items-center rounded-xl bg-cane-600 text-white">
              <Leaf className="size-5" />
            </span>
            <span className="font-display text-lg font-extrabold">
              Smart Sugarcane <span className="text-cane-600">AI</span>
            </span>
          </Link>

          <h1 className="font-display text-3xl font-extrabold">Welcome back</h1>
          <p className="mt-2 text-slate-600 dark:text-slate-400">
            Sign in to see your saved analyses and irrigation history.
          </p>

          {error && (
            <div className="mt-6">
              <Alert tone="danger">{error}</Alert>
            </div>
          )}

          <ServerAddress highlight={Boolean(error)} />

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <Field label="Email address" htmlFor="email">
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                className="input"
                placeholder="farmer@example.com"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </Field>

            <Field label="Password" htmlFor="password">
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  autoComplete="current-password"
                  className="input pr-11"
                  placeholder="Your password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 transition hover:text-slate-600 dark:hover:text-slate-200"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                </button>
              </div>
            </Field>

            <div className="flex justify-end">
              <button
                type="button"
                onClick={handleForgot}
                className="text-sm font-medium text-cane-700 hover:underline dark:text-cane-400"
              >
                Forgot password?
              </button>
            </div>

            <button type="submit" disabled={submitting} className="btn-primary w-full">
              {submitting ? <Spinner className="size-4" /> : <ArrowRight className="size-4" />}
              {submitting ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
            Do not have an account?{' '}
            <Link to="/register" className="font-semibold text-cane-700 hover:underline dark:text-cane-400">
              Create one
            </Link>
          </p>
        </div>
      </div>

      {/* Visual side */}
      <div className="relative hidden overflow-hidden bg-gradient-to-br from-cane-700 to-cane-950 lg:block">
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage:
              'radial-gradient(circle at 30% 20%, rgba(255,255,255,0.25), transparent 45%), radial-gradient(circle at 75% 70%, rgba(56,189,248,0.25), transparent 40%)',
          }}
        />
        <div className="relative flex h-full flex-col justify-center px-14">
          <h2 className="font-display text-4xl font-extrabold leading-tight text-white">
            Irrigate on measured need, not on the calendar.
          </h2>
          <p className="mt-6 max-w-md leading-relaxed text-cane-100">
            Enter your soil moisture and weather, and the system works out the water requirement, the
            duration and the priority - and shows you the calculation behind it.
          </p>
          <ul className="mt-10 space-y-4">
            {[
              'Water requirement in mm and litres, with duration',
              'Plant and soil photo analysis with honest confidence',
              'Variety and fertilizer guidance from an editable knowledge base',
              'Every result labelled with how it was produced',
            ].map((item) => (
              <li key={item} className="flex items-start gap-3 text-sm text-cane-50">
                <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-cane-300" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
