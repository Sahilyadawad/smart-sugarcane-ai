import { useState, type ReactNode } from 'react'
import { BrainCircuit, ChevronDown, FlaskConical, Info, Ruler } from 'lucide-react'
import type { ModelSource } from '../types'

/**
 * Compact, expandable provenance notice.
 *
 * The information here is required - every AI result must say how it was
 * produced. But two full-width amber panels stacked above the actual content
 * made the page read as "broken" rather than "carefully qualified". This
 * collapses the same text into one line the user can open, so the disclosure is
 * always present without dominating the screen.
 */

const CONFIG: Record<
  ModelSource,
  { title: string; icon: typeof Info; wrap: string; dot: string }
> = {
  trained_model: {
    title: 'Trained model',
    icon: BrainCircuit,
    wrap: 'border-cane-200 bg-cane-50/70 dark:border-cane-900 dark:bg-cane-950/40',
    dot: 'text-cane-700 dark:text-cane-300',
  },
  rule_engine: {
    title: 'Rule engine',
    icon: Ruler,
    wrap: 'border-sky-200 bg-sky-50/70 dark:border-sky-900 dark:bg-sky-950/40',
    dot: 'text-sky-700 dark:text-sky-300',
  },
  demo_heuristic: {
    title: 'Demo mode',
    icon: FlaskConical,
    wrap: 'border-amber-200 bg-amber-50/70 dark:border-amber-900/70 dark:bg-amber-950/30',
    dot: 'text-amber-700 dark:text-amber-300',
  },
}

export function HonestyNotice({
  source,
  summary,
  children,
  notes,
  defaultOpen = false,
}: {
  source: ModelSource
  /** One short line, always visible. */
  summary: string
  /** Longer explanation, revealed on expand. */
  children?: ReactNode
  notes?: string[]
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  const config = CONFIG[source] ?? CONFIG.demo_heuristic
  const Icon = config.icon
  const hasDetail = Boolean(children) || (notes?.length ?? 0) > 0

  return (
    <div className={`rounded-xl border ${config.wrap}`}>
      <button
        type="button"
        onClick={() => hasDetail && setOpen((value) => !value)}
        aria-expanded={hasDetail ? open : undefined}
        className={`flex w-full items-center gap-2.5 px-4 py-2.5 text-left ${
          hasDetail ? 'cursor-pointer' : 'cursor-default'
        }`}
      >
        <Icon className={`size-4 shrink-0 ${config.dot}`} aria-hidden />
        <span className={`text-xs font-bold uppercase tracking-wide ${config.dot}`}>
          {config.title}
        </span>
        <span className="min-w-0 flex-1 truncate text-sm text-slate-600 dark:text-slate-400">
          {summary}
        </span>
        {hasDetail && (
          <ChevronDown
            className={`size-4 shrink-0 text-slate-400 transition-transform ${open ? 'rotate-180' : ''}`}
            aria-hidden
          />
        )}
      </button>

      {open && hasDetail && (
        <div className="space-y-2 border-t border-black/5 px-4 py-3 text-sm leading-relaxed text-slate-600 dark:border-white/10 dark:text-slate-400">
          {children}
          {notes && notes.length > 0 && (
            <ul className="list-disc space-y-1 pl-5 text-xs">
              {notes.map((note, index) => (
                <li key={index}>{note}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
