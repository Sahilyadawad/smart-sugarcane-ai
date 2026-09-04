/** Small display helpers shared across pages. */

const LABELS: Record<string, string> = {
  alluvial: 'Alluvial Soil',
  black: 'Black Soil',
  red: 'Red Soil',
  sandy: 'Sandy Soil',
  clay: 'Clay Soil',
  loamy: 'Loamy Soil',
  mixed: 'Mixed / Unknown',
  germination: 'Germination / Establishment',
  tillering: 'Tillering',
  grand_growth: 'Grand Growth / Elongation',
  maturation: 'Maturation / Ripening',
  ratoon_initiation: 'Ratoon Initiation',
  clear: 'Clear',
  partly_cloudy: 'Partly Cloudy',
  cloudy: 'Cloudy',
  rainy: 'Rainy',
  stormy: 'Stormy',
  humid: 'Humid',
  dry_wind: 'Dry Wind',
  flood: 'Flood Irrigation',
  furrow: 'Furrow Irrigation',
  sprinkler: 'Sprinkler',
  drip: 'Drip Irrigation',
  tropical: 'Tropical',
  subtropical: 'Subtropical',
  semi_arid: 'Semi-arid',
  unknown: 'Not sure',
  adsali: 'Adsali',
  pre_seasonal: 'Pre-seasonal',
  suru: 'Suru',
  spring: 'Spring',
  autumn: 'Autumn',
  general: 'Any / not sure',
  low: 'Low',
  medium: 'Medium',
  high: 'High',
}

export function label(value?: string | null): string {
  if (!value) return 'Unknown'
  return (
    LABELS[value] ??
    value
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (character) => character.toUpperCase())
  )
}

export function percent(value: number | undefined | null, digits = 0): string {
  if (value === undefined || value === null || Number.isNaN(value)) return '-'
  return `${(value * 100).toFixed(digits)}%`
}

export function formatNumber(value: number | undefined | null, digits = 1): string {
  if (value === undefined || value === null || Number.isNaN(value)) return '-'
  return value.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

export function formatLitres(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)} million L`
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k L`
  return `${Math.round(value)} L`
}

export function formatDuration(minutes: number): string {
  if (minutes <= 0) return '-'
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return rest === 0 ? `${hours} h` : `${hours} h ${rest} min`
}

export function formatDate(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleDateString(undefined, { day: '2-digit', month: 'short', year: 'numeric' })
}

export function formatDateTime(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '-'
  return date.toLocaleString(undefined, {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function relativeTime(value?: string | null): string {
  if (!value) return ''
  const then = new Date(value).getTime()
  if (Number.isNaN(then)) return ''
  const diffMinutes = Math.round((Date.now() - then) / 60000)
  if (diffMinutes < 1) return 'just now'
  if (diffMinutes < 60) return `${diffMinutes} min ago`
  const hours = Math.round(diffMinutes / 60)
  if (hours < 24) return `${hours} h ago`
  const days = Math.round(hours / 24)
  if (days < 30) return `${days} d ago`
  return formatDate(value)
}

export const PRIORITY_TONE: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 border-red-200 dark:bg-red-950 dark:text-red-200 dark:border-red-900',
  high: 'bg-amber-100 text-amber-800 border-amber-200 dark:bg-amber-950 dark:text-amber-200 dark:border-amber-900',
  medium: 'bg-sky-100 text-sky-800 border-sky-200 dark:bg-sky-950 dark:text-sky-200 dark:border-sky-900',
  low: 'bg-cane-100 text-cane-800 border-cane-200 dark:bg-cane-950 dark:text-cane-200 dark:border-cane-900',
}

export const SEVERITY_TONE: Record<string, string> = {
  none: PRIORITY_TONE.low,
  mild: PRIORITY_TONE.medium,
  moderate: PRIORITY_TONE.high,
  severe: PRIORITY_TONE.critical,
  undetermined:
    'bg-slate-100 text-slate-700 border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700',
}
