import { useCallback, useEffect, useState } from 'react'
import {
  ChevronDown,
  ChevronUp,
  Droplets,
  History as HistoryIcon,
  Leaf,
  Mountain,
  Trash2,
} from 'lucide-react'
import { Alert, Badge, Card, EmptyState, Skeleton, Spinner } from '../components/ui'
import { useToast } from '../context/ToastContext'
import { describeError, mediaUrl } from '../services/api'
import { historyApi } from '../services/endpoints'
import { formatDateTime, relativeTime } from '../utils/format'
import type { HistoryDetail, HistoryItem, HistoryPage } from '../types'

const KIND_ICON = { plant: Leaf, soil: Mountain, irrigation: Droplets }

const TONE: Record<string, string> = {
  success: 'border-cane-300 bg-cane-100 text-cane-900 dark:border-cane-800 dark:bg-cane-950 dark:text-cane-200',
  warning:
    'border-amber-300 bg-amber-100 text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200',
  danger: 'border-red-300 bg-red-100 text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-200',
  info: 'border-sky-300 bg-sky-100 text-sky-900 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-200',
}

const FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'plant', label: 'Plant' },
  { value: 'soil', label: 'Soil' },
  { value: 'irrigation', label: 'Irrigation' },
]

function DetailView({ detail }: { detail: HistoryDetail }) {
  const payload = detail.payload as {
    inputs?: Record<string, unknown>
    result?: Record<string, unknown>
    image_url?: string
  }

  const renderValue = (value: unknown): string => {
    if (value === null || value === undefined) return '-'
    if (typeof value === 'boolean') return value ? 'Yes' : 'No'
    if (Array.isArray(value)) return value.map(String).join(', ')
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  return (
    <div className="space-y-4 border-t border-slate-100 bg-slate-50 p-5 dark:border-slate-800 dark:bg-slate-900/50">
      {payload.image_url && (
        <img
          src={mediaUrl(payload.image_url)}
          alt="Saved analysis"
          className="max-h-56 rounded-xl object-contain"
        />
      )}

      {payload.inputs && (
        <div>
          <h4 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Inputs</h4>
          <dl className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(payload.inputs).map(([key, value]) => (
              <div key={key} className="rounded-lg bg-white p-2.5 dark:bg-slate-800">
                <dt className="text-[11px] capitalize text-slate-500">{key.replace(/_/g, ' ')}</dt>
                <dd className="text-sm font-semibold">{renderValue(value)}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      {payload.result && (
        <div>
          <h4 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Result</h4>
          <dl className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(payload.result)
              .filter(
                ([key, value]) =>
                  typeof value !== 'object' &&
                  !['disclaimer', 'model_label', 'reason'].includes(key),
              )
              .map(([key, value]) => (
                <div key={key} className="rounded-lg bg-white p-2.5 dark:bg-slate-800">
                  <dt className="text-[11px] capitalize text-slate-500">{key.replace(/_/g, ' ')}</dt>
                  <dd className="text-sm font-semibold">{renderValue(value)}</dd>
                </div>
              ))}
          </dl>

          {typeof payload.result.reason === 'string' && (
            <p className="mt-3 rounded-lg bg-white p-3 text-sm leading-relaxed text-slate-600 dark:bg-slate-800 dark:text-slate-400">
              {payload.result.reason}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export default function HistoryPageView() {
  const toast = useToast()
  const [page, setPage] = useState<HistoryPage | null>(null)
  const [filter, setFilter] = useState('all')
  const [loading, setLoading] = useState(true)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [details, setDetails] = useState<Record<string, HistoryDetail>>({})
  const [busy, setBusy] = useState<string | null>(null)

  const load = useCallback(
    async (kind = filter) => {
      setLoading(true)
      try {
        setPage(await historyApi.list({ kind: kind === 'all' ? undefined : kind, page_size: 50 }))
      } catch (caught) {
        toast.error('Could not load history', describeError(caught))
      } finally {
        setLoading(false)
      }
    },
    [filter, toast],
  )

  useEffect(() => {
    void load(filter)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter])

  const toggle = async (item: HistoryItem) => {
    const key = `${item.kind}-${item.id}`
    if (expanded === key) {
      setExpanded(null)
      return
    }
    setExpanded(key)
    if (!details[key]) {
      try {
        const detail = await historyApi.detail(item.kind, item.id)
        setDetails((current) => ({ ...current, [key]: detail }))
      } catch (caught) {
        toast.error('Could not load details', describeError(caught))
      }
    }
  }

  const remove = async (item: HistoryItem) => {
    const key = `${item.kind}-${item.id}`
    setBusy(key)
    try {
      await historyApi.remove(item.kind, item.id)
      toast.success('Record deleted')
      setExpanded(null)
      await load(filter)
    } catch (caught) {
      toast.error('Could not delete', describeError(caught))
    } finally {
      setBusy(null)
    }
  }

  const clearAll = async () => {
    setBusy('all')
    try {
      const response = await historyApi.clearAll()
      toast.success('History cleared', response.detail)
      await load(filter)
    } catch (caught) {
      toast.error('Could not clear history', describeError(caught))
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl font-extrabold">History</h2>
          <p className="mt-1 text-slate-600 dark:text-slate-400">
            Every irrigation check, plant photo and soil analysis you have saved.
          </p>
        </div>
        {page && page.total > 0 && (
          <button
            type="button"
            onClick={clearAll}
            disabled={busy === 'all'}
            className="btn-secondary text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-950"
          >
            {busy === 'all' ? <Spinner className="size-3.5" /> : <Trash2 className="size-3.5" />}
            Delete all records
          </button>
        )}
      </div>

      {page && (
        <div className="grid gap-4 sm:grid-cols-4">
          {[
            { label: 'Total', value: page.counts.total, icon: HistoryIcon, tone: 'text-slate-600' },
            { label: 'Irrigation', value: page.counts.irrigation, icon: Droplets, tone: 'text-sky-600' },
            { label: 'Plant', value: page.counts.plant, icon: Leaf, tone: 'text-cane-600' },
            { label: 'Soil', value: page.counts.soil, icon: Mountain, tone: 'text-soil-600' },
          ].map((stat) => {
            const Icon = stat.icon
            return (
              <Card key={stat.label} className="flex items-center gap-3 p-4">
                <Icon className={`size-5 ${stat.tone}`} />
                <div>
                  <p className="font-display text-xl font-extrabold">{stat.value}</p>
                  <p className="text-xs text-slate-500">{stat.label}</p>
                </div>
              </Card>
            )
          })}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => setFilter(option.value)}
            className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
              filter === option.value
                ? 'bg-cane-600 text-white shadow-sm'
                : 'bg-white text-slate-600 hover:bg-slate-100 dark:bg-slate-900 dark:text-slate-400 dark:hover:bg-slate-800'
            }`}
          >
            {option.label}
          </button>
        ))}
      </div>

      <Card>
        {loading ? (
          <div className="space-y-3 p-5">
            {[0, 1, 2, 3].map((index) => (
              <Skeleton key={index} className="h-20 w-full" />
            ))}
          </div>
        ) : !page || page.items.length === 0 ? (
          <EmptyState
            icon={HistoryIcon}
            title="Nothing saved yet"
            description={
              filter === 'all'
                ? 'Run an irrigation check or upload a photo and it will appear here automatically.'
                : `No ${filter} records yet. Switch the filter to "All" to see everything.`
            }
          />
        ) : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {page.items.map((item) => {
              const key = `${item.kind}-${item.id}`
              const Icon = KIND_ICON[item.kind]
              const isOpen = expanded === key
              return (
                <li key={key}>
                  <div className="flex items-center gap-4 p-4 transition hover:bg-slate-50 dark:hover:bg-slate-800/50">
                    {item.image_url ? (
                      <img
                        src={mediaUrl(item.image_url)}
                        alt={item.title}
                        className="size-14 shrink-0 rounded-xl object-cover"
                      />
                    ) : (
                      <span className="grid size-14 shrink-0 place-items-center rounded-xl bg-sky-50 text-sky-600 dark:bg-sky-950 dark:text-sky-400">
                        <Icon className="size-6" />
                      </span>
                    )}

                    <button
                      type="button"
                      onClick={() => void toggle(item)}
                      className="min-w-0 flex-1 text-left"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="truncate font-semibold">{item.title}</p>
                        <Badge className={TONE[item.badge_tone]}>{item.badge}</Badge>
                      </div>
                      <p className="mt-0.5 truncate text-xs text-slate-500 dark:text-slate-400">
                        {item.subtitle}
                      </p>
                      <p className="mt-0.5 text-xs text-slate-400">
                        {formatDateTime(item.created_at)} | {relativeTime(item.created_at)}
                      </p>
                    </button>

                    <div className="flex shrink-0 items-center gap-1">
                      <button
                        type="button"
                        onClick={() => void toggle(item)}
                        className="grid size-9 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800"
                        aria-label={isOpen ? 'Hide details' : 'Show details'}
                      >
                        {isOpen ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
                      </button>
                      <button
                        type="button"
                        onClick={() => void remove(item)}
                        disabled={busy === key}
                        className="grid size-9 place-items-center rounded-lg text-slate-400 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950"
                        aria-label="Delete this record"
                      >
                        {busy === key ? <Spinner className="size-4" /> : <Trash2 className="size-4" />}
                      </button>
                    </div>
                  </div>

                  {isOpen &&
                    (details[key] ? (
                      <DetailView detail={details[key]} />
                    ) : (
                      <div className="flex justify-center border-t border-slate-100 p-6 dark:border-slate-800">
                        <Spinner className="size-5 text-cane-600" />
                      </div>
                    ))}
                </li>
              )
            })}
          </ul>
        )}
      </Card>

      <Alert tone="info" title="Where this data lives">
        Records are stored in the local SQLite database at{' '}
        <code>backend/smart_sugarcane.db</code>, and uploaded images in the <code>uploads/</code>{' '}
        folder. Deleting a record here also deletes its image file. Nothing is sent anywhere else.
      </Alert>
    </div>
  )
}
