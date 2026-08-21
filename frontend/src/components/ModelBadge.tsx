import { BrainCircuit, FlaskConical, Ruler } from 'lucide-react'
import { Alert, Badge } from './ui'
import type { ModelSource } from '../types'

/**
 * The single place the UI states how a result was produced. Nothing in this app
 * shows an AI answer without one of these next to it.
 */
const CONFIG: Record<
  ModelSource,
  { label: string; icon: typeof BrainCircuit; classes: string; blurb: string }
> = {
  trained_model: {
    label: 'Trained model',
    icon: BrainCircuit,
    classes:
      'border-cane-200 bg-cane-50 text-cane-800 dark:border-cane-800 dark:bg-cane-950 dark:text-cane-200',
    blurb: 'Produced by a trained machine-learning model loaded from the models/ directory.',
  },
  rule_engine: {
    label: 'Rule engine',
    icon: Ruler,
    classes:
      'border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-200',
    blurb:
      'Produced by the documented water-balance calculation, not a machine-learning model. Every coefficient is inspectable.',
  },
  demo_heuristic: {
    label: 'DEMO mode',
    icon: FlaskConical,
    classes:
      'border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200',
    blurb:
      'Produced by a transparent colour and texture heuristic, not a trained neural network. Illustrative only - never treat it as a diagnosis.',
  },
}

export function ModelBadge({ source }: { source: ModelSource }) {
  const config = CONFIG[source] ?? CONFIG.demo_heuristic
  const Icon = config.icon
  return (
    <Badge className={config.classes}>
      <Icon className="size-3.5" aria-hidden />
      {config.label}
    </Badge>
  )
}

export function ModelNotice({
  source,
  label,
  notes,
}: {
  source: ModelSource
  label?: string
  notes?: string[]
}) {
  const config = CONFIG[source] ?? CONFIG.demo_heuristic
  const tone = source === 'demo_heuristic' ? 'warning' : source === 'rule_engine' ? 'info' : 'success'
  return (
    <Alert tone={tone} title={label || config.label} icon={config.icon}>
      <p>{config.blurb}</p>
      {notes && notes.length > 0 && (
        <ul className="mt-2 list-disc space-y-1 pl-4 text-xs opacity-90">
          {notes.map((note, index) => (
            <li key={index}>{note}</li>
          ))}
        </ul>
      )}
    </Alert>
  )
}
