import { useState, type FormEvent } from 'react'
import { Check, Server } from 'lucide-react'
import { API_BASE_URL, normaliseServerAddress, serverAddressStore } from '../services/api'

/**
 * Lets the user point the app at the machine running the backend.
 *
 * In the packaged Android app the backend address is whatever the current
 * network assigns to the laptop, and it changes whenever the network does.
 * Baking it in at build time meant every change required a new APK, so the
 * address is editable here and stored in localStorage instead.
 */
export function ServerAddress({ highlight = false }: { highlight?: boolean }) {
  const current = API_BASE_URL.replace(/^https?:\/\//, '').replace(/\/api$/, '')
  const [open, setOpen] = useState(highlight)
  const [value, setValue] = useState(current)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    try {
      const resolved = normaliseServerAddress(value)
      if (!resolved) {
        setError('Enter the address of the computer running the backend.')
        return
      }
      serverAddressStore.set(value)
      setSaved(true)
      // A full reload is the simplest way to rebuild the axios client and every
      // module that captured the old base URL at import time.
      setTimeout(() => window.location.reload(), 450)
    } catch {
      setError('That does not look like a valid address. Try 192.168.1.5:8000')
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="mt-4 inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-cane-700 dark:text-slate-400 dark:hover:text-cane-400"
      >
        <Server className="size-3.5" />
        Server: {current} — change
      </button>
    )
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-3.5 dark:border-slate-700 dark:bg-slate-800/60"
    >
      <label
        htmlFor="server-address"
        className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 dark:text-slate-200"
      >
        <Server className="size-3.5" />
        Server address
      </label>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        The computer running the backend. Find it with <code>ipconfig</code> on that machine, and
        make sure this device is on the same Wi-Fi.
      </p>
      <div className="mt-2 flex gap-2">
        <input
          id="server-address"
          className="input flex-1 !py-1.5 text-sm"
          placeholder="192.168.1.5:8000"
          value={value}
          onChange={(event) => setValue(event.target.value)}
          autoCapitalize="none"
          autoCorrect="off"
          spellCheck={false}
          inputMode="url"
        />
        <button type="submit" className="btn-primary !py-1.5 !px-3 text-sm">
          {saved ? <Check className="size-4" /> : 'Save'}
        </button>
      </div>
      {error && <p className="mt-1.5 text-xs font-medium text-rose-600 dark:text-rose-400">{error}</p>}
      {saved && (
        <p className="mt-1.5 text-xs font-medium text-cane-700 dark:text-cane-400">
          Saved — reloading…
        </p>
      )}
    </form>
  )
}
