import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ArrowRight, Eye, EyeOff, Leaf } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { describeError } from '../services/api'
import { Alert, Field, Spinner } from '../components/ui'
import { ServerAddress } from '../components/ServerAddress'

export default function Register() {
  const { register } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    name: '',
    email: '',
    password: '',
    confirm: '',
    phone: '',
    farm_location: '',
  })
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const update = (key: keyof typeof form) => (event: { target: { value: string } }) =>
    setForm((current) => ({ ...current, [key]: event.target.value }))

  const passwordProblem =
    form.password.length > 0 && form.password.length < 8
      ? 'Use at least 8 characters.'
      : form.confirm.length > 0 && form.confirm !== form.password
        ? 'The two passwords do not match.'
        : null

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    if (passwordProblem) {
      setError(passwordProblem)
      return
    }
    setSubmitting(true)
    try {
      await register({
        name: form.name.trim(),
        email: form.email.trim(),
        password: form.password,
        phone: form.phone.trim() || undefined,
        farm_location: form.farm_location.trim() || undefined,
      })
      toast.success('Account created', 'Welcome to Smart Sugarcane AI.')
      navigate('/dashboard', { replace: true })
    } catch (caught) {
      setError(describeError(caught, 'Registration failed.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
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

          <h1 className="font-display text-3xl font-extrabold">Create your account</h1>
          <p className="mt-2 text-slate-600 dark:text-slate-400">
            Free, and stored only on your own machine while you run this locally.
          </p>

          {error && (
            <div className="mt-6">
              <Alert tone="danger">{error}</Alert>
            </div>
          )}

          <ServerAddress highlight={Boolean(error)} />

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <Field label="Full name" htmlFor="name">
              <input
                id="name"
                required
                minLength={2}
                autoComplete="name"
                className="input"
                placeholder="Sudeep K"
                value={form.name}
                onChange={update('name')}
              />
            </Field>

            <Field label="Email address" htmlFor="email">
              <input
                id="email"
                type="email"
                required
                autoComplete="email"
                className="input"
                placeholder="farmer@example.com"
                value={form.email}
                onChange={update('email')}
              />
            </Field>

            <Field label="Password" htmlFor="password" hint="At least 8 characters.">
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  minLength={8}
                  autoComplete="new-password"
                  className="input pr-11"
                  value={form.password}
                  onChange={update('password')}
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

            <Field label="Confirm password" htmlFor="confirm">
              <input
                id="confirm"
                type={showPassword ? 'text' : 'password'}
                required
                autoComplete="new-password"
                className="input"
                value={form.confirm}
                onChange={update('confirm')}
              />
            </Field>

            {passwordProblem && (
              <p className="text-sm font-medium text-amber-600 dark:text-amber-400">{passwordProblem}</p>
            )}

            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Phone (optional)" htmlFor="phone">
                <input
                  id="phone"
                  className="input"
                  value={form.phone}
                  onChange={update('phone')}
                />
              </Field>
              <Field label="Farm location (optional)" htmlFor="farm">
                <input
                  id="farm"
                  className="input"
                  placeholder="Belagavi, Karnataka"
                  value={form.farm_location}
                  onChange={update('farm_location')}
                />
              </Field>
            </div>
            <p className="-mt-2 text-xs text-slate-500 dark:text-slate-400">
              Farm location is also used as the city for live weather, if you configure a weather API key.
            </p>

            <button type="submit" disabled={submitting} className="btn-primary w-full">
              {submitting ? <Spinner className="size-4" /> : <ArrowRight className="size-4" />}
              {submitting ? 'Creating account...' : 'Create account'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-600 dark:text-slate-400">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-cane-700 hover:underline dark:text-cane-400">
              Sign in
            </Link>
          </p>
        </div>
      </div>

      <div className="relative hidden overflow-hidden bg-gradient-to-br from-cane-700 to-cane-950 lg:block">
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage:
              'radial-gradient(circle at 70% 25%, rgba(255,255,255,0.22), transparent 45%), radial-gradient(circle at 25% 75%, rgba(34,197,94,0.35), transparent 40%)',
          }}
        />
        <div className="relative flex h-full flex-col justify-center px-14">
          <h2 className="font-display text-4xl font-extrabold leading-tight text-white">
            One account, one season of records.
          </h2>
          <p className="mt-6 max-w-md leading-relaxed text-cane-100">
            Every irrigation check, plant photo and soil analysis is saved against your account, so
            you can compare a block against itself over time instead of relying on memory.
          </p>
          <ul className="mt-10 space-y-4">
            {[
              'Plant health trend across repeat photos',
              'Irrigation history with soil moisture and water applied',
              'Variety shortlists saved with the soil they were based on',
              'Delete everything at any time from Settings',
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
