import { useEffect, useState, type FormEvent } from 'react'
import {
  Activity,
  Bell,
  Database,
  Globe,
  KeyRound,
  Monitor,
  Moon,
  Save,
  Shield,
  Sun,
  Trash2,
  User as UserIcon,
} from 'lucide-react'
import { Alert, Badge, Card, CardHeader, Field, Spinner } from '../components/ui'
import { ModelBadge } from '../components/ModelBadge'
import { useAuth } from '../context/AuthContext'
import { useToast } from '../context/ToastContext'
import { useTheme, type Theme } from '../hooks/useTheme'
import { describeError } from '../services/api'
import { authApi, historyApi, systemApi } from '../services/endpoints'
import { formatDate } from '../utils/format'
import type { ModelSource, SystemStatus } from '../types'

const THEMES: { value: Theme; label: string; icon: typeof Sun }[] = [
  { value: 'light', label: 'Light', icon: Sun },
  { value: 'dark', label: 'Dark', icon: Moon },
  { value: 'system', label: 'System', icon: Monitor },
]

const LANGUAGES = [
  { value: 'en', label: 'English', available: true },
  { value: 'kn', label: 'Kannada', available: false },
  { value: 'hi', label: 'Hindi', available: false },
]

export default function Settings() {
  const { user, setUser } = useAuth()
  const toast = useToast()
  const { theme, setTheme } = useTheme()

  const [profile, setProfile] = useState({
    name: user?.name ?? '',
    phone: user?.phone ?? '',
    farm_location: user?.farm_location ?? '',
  })
  const [notifications, setNotifications] = useState(user?.notifications_enabled ?? true)
  const [language, setLanguage] = useState(user?.language ?? 'en')
  const [savingProfile, setSavingProfile] = useState(false)

  const [passwords, setPasswords] = useState({ current: '', next: '', confirm: '' })
  const [savingPassword, setSavingPassword] = useState(false)

  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [clearing, setClearing] = useState(false)

  useEffect(() => {
    systemApi.status().then(setStatus).catch(() => setStatus(null))
  }, [])

  const saveProfile = async (event: FormEvent) => {
    event.preventDefault()
    setSavingProfile(true)
    try {
      const updated = await authApi.updateProfile({
        name: profile.name.trim(),
        phone: profile.phone.trim() || undefined,
        farm_location: profile.farm_location.trim() || undefined,
        notifications_enabled: notifications,
        language,
        theme,
      })
      setUser(updated)
      toast.success('Settings saved')
    } catch (caught) {
      toast.error('Could not save settings', describeError(caught))
    } finally {
      setSavingProfile(false)
    }
  }

  const savePassword = async (event: FormEvent) => {
    event.preventDefault()
    if (passwords.next !== passwords.confirm) {
      toast.error('Passwords do not match', 'Retype the new password to confirm it.')
      return
    }
    if (passwords.next.length < 8) {
      toast.error('Password too short', 'Use at least 8 characters.')
      return
    }
    setSavingPassword(true)
    try {
      const response = await authApi.changePassword({
        current_password: passwords.current,
        new_password: passwords.next,
      })
      toast.success('Password changed', response.detail)
      setPasswords({ current: '', next: '', confirm: '' })
    } catch (caught) {
      toast.error('Could not change password', describeError(caught))
    } finally {
      setSavingPassword(false)
    }
  }

  const clearData = async () => {
    setClearing(true)
    try {
      const response = await historyApi.clearAll()
      toast.success('Data deleted', response.detail)
    } catch (caught) {
      toast.error('Could not delete data', describeError(caught))
    } finally {
      setClearing(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-2xl font-extrabold">Settings</h2>
        <p className="mt-1 text-slate-600 dark:text-slate-400">
          Profile, appearance, language, notifications and your data.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Profile */}
        <Card>
          <CardHeader title="Profile" subtitle="Your details" icon={UserIcon} />
          <form onSubmit={saveProfile} className="space-y-4 p-5">
            <Field label="Full name" htmlFor="name">
              <input
                id="name"
                className="input"
                value={profile.name}
                onChange={(event) => setProfile((c) => ({ ...c, name: event.target.value }))}
              />
            </Field>

            <Field label="Email" htmlFor="email" hint="The email address cannot be changed.">
              <input id="email" className="input" value={user?.email ?? ''} disabled />
            </Field>

            <Field label="Phone" htmlFor="phone">
              <input
                id="phone"
                className="input"
                value={profile.phone}
                onChange={(event) => setProfile((c) => ({ ...c, phone: event.target.value }))}
              />
            </Field>

            <Field
              label="Farm location"
              htmlFor="farm"
              hint="Also used as the city for live weather, if a weather API key is configured."
            >
              <input
                id="farm"
                className="input"
                placeholder="Belagavi, Karnataka"
                value={profile.farm_location}
                onChange={(event) => setProfile((c) => ({ ...c, farm_location: event.target.value }))}
              />
            </Field>

            {/* Theme */}
            <div>
              <p className="label">Theme</p>
              <div className="grid grid-cols-3 gap-2">
                {THEMES.map((option) => {
                  const Icon = option.icon
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setTheme(option.value)}
                      className={`flex flex-col items-center gap-1.5 rounded-xl border p-3 text-xs font-semibold transition ${
                        theme === option.value
                          ? 'border-cane-500 bg-cane-50 text-cane-800 dark:bg-cane-950 dark:text-cane-200'
                          : 'border-slate-200 text-slate-600 hover:bg-slate-50 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-800'
                      }`}
                    >
                      <Icon className="size-4" />
                      {option.label}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Language */}
            <div>
              <p className="label">
                <Globe className="mr-1 inline size-3.5" />
                Language
              </p>
              <div className="space-y-2">
                {LANGUAGES.map((option) => (
                  <label
                    key={option.value}
                    className={`flex items-center justify-between rounded-xl border p-3 text-sm ${
                      option.available
                        ? 'cursor-pointer border-slate-200 hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800'
                        : 'cursor-not-allowed border-slate-200 opacity-60 dark:border-slate-800'
                    }`}
                  >
                    <span className="flex items-center gap-2.5">
                      <input
                        type="radio"
                        name="language"
                        className="size-4 accent-cane-600"
                        value={option.value}
                        checked={language === option.value}
                        disabled={!option.available}
                        onChange={() => setLanguage(option.value)}
                      />
                      {option.label}
                    </span>
                    {!option.available && (
                      <Badge className="border-slate-200 bg-slate-100 text-slate-500 dark:border-slate-700 dark:bg-slate-800">
                        Planned
                      </Badge>
                    )}
                  </label>
                ))}
              </div>
              <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                Only English is implemented today. The assistant and interface are structured so
                Kannada and Hindi can be added - the app says so rather than shipping a half-translated
                interface.
              </p>
            </div>

            {/* Notifications */}
            <label className="flex items-start gap-3 rounded-xl border border-slate-200 p-4 dark:border-slate-700">
              <input
                type="checkbox"
                className="mt-0.5 size-4 rounded accent-cane-600"
                checked={notifications}
                onChange={(event) => setNotifications(event.target.checked)}
              />
              <span>
                <span className="flex items-center gap-1.5 text-sm font-semibold">
                  <Bell className="size-3.5" />
                  In-app notifications
                </span>
                <span className="mt-1 block text-xs text-slate-500 dark:text-slate-400">
                  Show toast messages for analysis results and errors. This is a local preference -
                  no emails or SMS are sent by this application.
                </span>
              </span>
            </label>

            <button type="submit" disabled={savingProfile} className="btn-primary w-full">
              {savingProfile ? <Spinner className="size-4" /> : <Save className="size-4" />}
              Save settings
            </button>
          </form>
        </Card>

        <div className="space-y-6">
          {/* Password */}
          <Card>
            <CardHeader title="Change password" icon={KeyRound} />
            <form onSubmit={savePassword} className="space-y-4 p-5">
              <Field label="Current password" htmlFor="current">
                <input
                  id="current"
                  type="password"
                  required
                  autoComplete="current-password"
                  className="input"
                  value={passwords.current}
                  onChange={(event) => setPasswords((c) => ({ ...c, current: event.target.value }))}
                />
              </Field>
              <Field label="New password" htmlFor="next" hint="At least 8 characters.">
                <input
                  id="next"
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  className="input"
                  value={passwords.next}
                  onChange={(event) => setPasswords((c) => ({ ...c, next: event.target.value }))}
                />
              </Field>
              <Field label="Confirm new password" htmlFor="confirm">
                <input
                  id="confirm"
                  type="password"
                  required
                  autoComplete="new-password"
                  className="input"
                  value={passwords.confirm}
                  onChange={(event) => setPasswords((c) => ({ ...c, confirm: event.target.value }))}
                />
              </Field>
              <button type="submit" disabled={savingPassword} className="btn-secondary w-full">
                {savingPassword ? <Spinner className="size-4" /> : <KeyRound className="size-4" />}
                Update password
              </button>
            </form>
          </Card>

          {/* AI status */}
          <Card>
            <CardHeader title="AI model status" subtitle="What is actually running" icon={Activity} />
            {status ? (
              <div className="space-y-3 p-5 text-sm">
                {(
                  [
                    ['Irrigation', status.models.irrigation],
                    ['Disease detection', status.models.disease],
                    ['Soil analysis', status.models.soil],
                  ] as const
                ).map(([name, model]) => (
                  <div
                    key={name}
                    className="flex items-start justify-between gap-3 border-b border-slate-100 pb-3 last:border-0 last:pb-0 dark:border-slate-800"
                  >
                    <div className="min-w-0">
                      <p className="font-semibold">{name}</p>
                      <p className="truncate text-xs text-slate-500">{model.model_path}</p>
                    </div>
                    <ModelBadge source={model.model_source as ModelSource} />
                  </div>
                ))}
                <div className="grid grid-cols-2 gap-2 pt-2 text-xs text-slate-500">
                  <span>Version {status.version}</span>
                  <span>Python {status.python}</span>
                  <span>Mode: {status.model_mode}</span>
                  <span>OpenCV: {status.opencv_available ? 'yes' : 'no'}</span>
                </div>
                <Alert tone="info">{status.honesty_notice}</Alert>
              </div>
            ) : (
              <div className="p-5">
                <p className="text-sm text-slate-500">
                  Could not reach the backend to read model status.
                </p>
              </div>
            )}
          </Card>

          {/* Data & privacy */}
          <Card className="border-red-200 dark:border-red-900">
            <CardHeader title="Data and privacy" icon={Shield} />
            <div className="space-y-4 p-5">
              <div className="flex gap-3 text-sm">
                <Database className="mt-0.5 size-4 shrink-0 text-slate-400" />
                <div>
                  <p className="font-semibold">Everything stays on this machine</p>
                  <p className="mt-1 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                    Your account, analyses and uploaded photos are stored in a local SQLite database
                    and the local <code>uploads/</code> folder. The only outbound request this
                    application can make is to a weather API, and only if you configure a key.
                  </p>
                </div>
              </div>

              {user && (
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Account created {formatDate(user.created_at)}.
                </p>
              )}

              <div className="rounded-xl border border-red-200 bg-red-50 p-4 dark:border-red-900 dark:bg-red-950/40">
                <p className="text-sm font-semibold text-red-900 dark:text-red-200">
                  Delete all my analyses
                </p>
                <p className="mt-1 text-xs leading-relaxed text-red-800/80 dark:text-red-300/80">
                  Permanently removes every irrigation record, plant analysis and soil analysis, plus
                  the uploaded image files. Your account stays. This cannot be undone.
                </p>
                <button
                  type="button"
                  onClick={clearData}
                  disabled={clearing}
                  className="btn mt-3 w-full bg-red-600 text-white hover:bg-red-700"
                >
                  {clearing ? <Spinner className="size-4" /> : <Trash2 className="size-4" />}
                  Delete all my data
                </button>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
