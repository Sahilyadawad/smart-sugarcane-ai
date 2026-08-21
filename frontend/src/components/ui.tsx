import type { ComponentType, ReactNode } from 'react'
import { AlertTriangle, Info, Loader2, TriangleAlert } from 'lucide-react'

// ------------------------------------------------------------------ card
export function Card({
  children,
  className = '',
  hover = false,
}: {
  children: ReactNode
  className?: string
  hover?: boolean
}) {
  return <div className={`card ${hover ? 'card-hover' : ''} ${className}`}>{children}</div>
}

export function CardHeader({
  title,
  subtitle,
  icon: Icon,
  action,
}: {
  title: string
  subtitle?: string
  icon?: ComponentType<{ className?: string }>
  action?: ReactNode
}) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-slate-100 p-5 dark:border-slate-800">
      <div className="flex min-w-0 items-start gap-3">
        {Icon && (
          <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-cane-50 text-cane-700 dark:bg-cane-950 dark:text-cane-300">
            <Icon className="size-5" />
          </span>
        )}
        <div className="min-w-0">
          <h3 className="truncate text-base font-bold">{title}</h3>
          {subtitle && (
            <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>
          )}
        </div>
      </div>
      {action}
    </div>
  )
}

// ----------------------------------------------------------------- badge
export function Badge({
  children,
  className = '',
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${
        className ||
        'border-slate-200 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300'
      }`}
    >
      {children}
    </span>
  )
}

// -------------------------------------------------------------- stat card
export function StatCard({
  label,
  value,
  unit,
  icon: Icon,
  tone = 'default',
  hint,
}: {
  label: string
  value: string | number
  unit?: string
  icon?: ComponentType<{ className?: string }>
  tone?: 'default' | 'green' | 'blue' | 'amber' | 'red'
  hint?: string
}) {
  const tones: Record<string, string> = {
    default: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
    green: 'bg-cane-100 text-cane-700 dark:bg-cane-950 dark:text-cane-300',
    blue: 'bg-sky-100 text-sky-700 dark:bg-sky-950 dark:text-sky-300',
    amber: 'bg-amber-100 text-amber-700 dark:bg-amber-950 dark:text-amber-300',
    red: 'bg-red-100 text-red-700 dark:bg-red-950 dark:text-red-300',
  }
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            {label}
          </p>
          <p className="mt-2 font-display text-2xl font-extrabold text-slate-900 dark:text-white">
            {value}
            {unit && <span className="ml-1 text-sm font-semibold text-slate-500">{unit}</span>}
          </p>
          {hint && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
        </div>
        {Icon && (
          <span className={`grid size-11 shrink-0 place-items-center rounded-xl ${tones[tone]}`}>
            <Icon className="size-5" />
          </span>
        )}
      </div>
    </Card>
  )
}

// ----------------------------------------------------------------- alert
export function Alert({
  tone = 'info',
  title,
  children,
  icon: Icon,
}: {
  tone?: 'info' | 'warning' | 'danger' | 'success'
  title?: string
  children: ReactNode
  icon?: ComponentType<{ className?: string }>
}) {
  const styles: Record<string, string> = {
    info: 'border-sky-200 bg-sky-50 text-sky-900 dark:border-sky-900 dark:bg-sky-950/60 dark:text-sky-100',
    warning:
      'border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900 dark:bg-amber-950/60 dark:text-amber-100',
    danger: 'border-red-200 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950/60 dark:text-red-100',
    success:
      'border-cane-200 bg-cane-50 text-cane-900 dark:border-cane-900 dark:bg-cane-950/60 dark:text-cane-100',
  }
  const DefaultIcon = tone === 'info' ? Info : tone === 'success' ? Info : AlertTriangle
  const Chosen = Icon ?? DefaultIcon

  return (
    <div className={`flex gap-3 rounded-xl border p-4 text-sm ${styles[tone]}`}>
      <Chosen className="mt-0.5 size-5 shrink-0" aria-hidden />
      <div className="min-w-0 flex-1 leading-relaxed">
        {title && <p className="mb-1 font-semibold">{title}</p>}
        {children}
      </div>
    </div>
  )
}

// --------------------------------------------------------------- loading
export function Spinner({ className = 'size-5' }: { className?: string }) {
  return <Loader2 className={`animate-spin ${className}`} aria-hidden />
}

export function LoadingBlock({ label = 'Loading...' }: { label?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-slate-500 dark:text-slate-400">
      <Spinner className="size-8 text-cane-600" />
      <p className="text-sm">{label}</p>
    </div>
  )
}

export function Skeleton({ className = 'h-4 w-full' }: { className?: string }) {
  return <div className={`skeleton ${className}`} />
}

export function SkeletonCard() {
  return (
    <Card className="space-y-3 p-5">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-8 w-32" />
      <Skeleton className="h-3 w-40" />
    </Card>
  )
}

// ------------------------------------------------------------ empty state
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
}: {
  icon: ComponentType<{ className?: string }>
  title: string
  description: string
  action?: ReactNode
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 px-6 py-14 text-center">
      <span className="grid size-14 place-items-center rounded-2xl bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
        <Icon className="size-7" />
      </span>
      <h4 className="text-base font-bold">{title}</h4>
      <p className="max-w-md text-sm text-slate-500 dark:text-slate-400">{description}</p>
      {action}
    </div>
  )
}

// ---------------------------------------------------------------- fields
export function Field({
  label: fieldLabel,
  hint,
  children,
  htmlFor,
}: {
  label: string
  hint?: string
  children: ReactNode
  htmlFor?: string
}) {
  return (
    <div>
      <label className="label" htmlFor={htmlFor}>
        {fieldLabel}
      </label>
      {children}
      {hint && <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
    </div>
  )
}

export function ProgressBar({
  value,
  tone = 'green',
  showLabel = false,
}: {
  value: number
  tone?: 'green' | 'amber' | 'red' | 'blue'
  showLabel?: boolean
}) {
  const clamped = Math.max(0, Math.min(100, value))
  const tones: Record<string, string> = {
    green: 'bg-cane-500',
    amber: 'bg-amber-500',
    red: 'bg-red-500',
    blue: 'bg-sky-500',
  }
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
        <div
          className={`h-full rounded-full transition-all duration-500 ${tones[tone]}`}
          style={{ width: `${clamped}%` }}
        />
      </div>
      {showLabel && (
        <span className="w-11 shrink-0 text-right text-xs font-semibold tabular-nums text-slate-600 dark:text-slate-400">
          {clamped.toFixed(0)}%
        </span>
      )}
    </div>
  )
}

// ------------------------------------------------------------- list block
export function BulletList({
  items,
  tone = 'default',
}: {
  items: string[]
  tone?: 'default' | 'warning' | 'success'
}) {
  const dot: Record<string, string> = {
    default: 'bg-slate-300 dark:bg-slate-600',
    warning: 'bg-amber-400',
    success: 'bg-cane-500',
  }
  if (!items?.length) return null
  return (
    <ul className="prose-list">
      {items.map((item, index) => (
        <li key={index} className="flex gap-2.5">
          <span className={`mt-[7px] size-1.5 shrink-0 rounded-full ${dot[tone]}`} />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  )
}

export function NumberedList({ items }: { items: string[] }) {
  if (!items?.length) return null
  return (
    <ol className="space-y-3">
      {items.map((item, index) => (
        <li key={index} className="flex gap-3 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          <span className="grid size-6 shrink-0 place-items-center rounded-lg bg-cane-100 text-xs font-bold text-cane-800 dark:bg-cane-950 dark:text-cane-300">
            {index + 1}
          </span>
          <span>{item}</span>
        </li>
      ))}
    </ol>
  )
}

export function Disclaimer({ children }: { children: ReactNode }) {
  return (
    <div className="flex gap-2.5 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-xs leading-relaxed text-amber-900 dark:border-amber-900 dark:bg-amber-950/50 dark:text-amber-200">
      <TriangleAlert className="mt-0.5 size-4 shrink-0" aria-hidden />
      <p>{children}</p>
    </div>
  )
}
