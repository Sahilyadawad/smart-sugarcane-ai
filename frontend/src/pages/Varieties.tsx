import { useEffect, useState, type FormEvent } from 'react'
import {
  Award,
  Building2,
  CalendarDays,
  Clock,
  Droplets,
  Info,
  Search,
  ShieldAlert,
  Sprout,
  ThumbsUp,
} from 'lucide-react'
import {
  Alert,
  Badge,
  Card,
  CardHeader,
  EmptyState,
  Field,
  ProgressBar,
  Spinner,
} from '../components/ui'
import { useToast } from '../context/ToastContext'
import { describeError } from '../services/api'
import { recommendationApi } from '../services/endpoints'
import { label } from '../utils/format'
import type {
  ClimateType,
  PlantingSeason,
  SoilType,
  VarietyMatch,
  VarietyRecommendation,
  WaterAvailability,
} from '../types'

const SOILS: SoilType[] = ['black', 'red', 'sandy', 'clay', 'loamy', 'mixed']
const CLIMATES: ClimateType[] = ['unknown', 'tropical', 'subtropical', 'semi_arid']
const WATER: WaterAvailability[] = ['low', 'medium', 'high']
const SEASONS: PlantingSeason[] = ['general', 'adsali', 'pre_seasonal', 'suru', 'spring', 'autumn']

const MATCH_TONE: Record<string, string> = {
  'Best Match': 'border-cane-300 bg-cane-100 text-cane-900 dark:border-cane-800 dark:bg-cane-950 dark:text-cane-200',
  'Good Match': 'border-sky-300 bg-sky-100 text-sky-900 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-200',
  Alternative: 'border-slate-300 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300',
  'Weak Match': 'border-amber-300 bg-amber-100 text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200',
}

/** Shared by this page and the Soil Analysis page. */
export function VarietyCard({ match }: { match: VarietyMatch }) {
  return (
    <div className="flex h-full flex-col rounded-2xl border border-slate-200 p-5 transition hover:border-cane-300 dark:border-slate-800 dark:hover:border-cane-800">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h4 className="font-display text-lg font-extrabold">{match.name}</h4>
          {match.aliases.length > 0 && (
            <p className="text-xs text-slate-500">also known as {match.aliases.join(', ')}</p>
          )}
        </div>
        <Badge className={MATCH_TONE[match.match_label] ?? MATCH_TONE.Alternative}>
          <Award className="size-3.5" />
          {match.match_label}
        </Badge>
      </div>

      <div className="mt-3">
        <div className="mb-1 flex justify-between text-xs font-medium">
          <span className="text-slate-500">Recommendation score</span>
          <span className="tabular-nums">{match.match_score.toFixed(0)}%</span>
        </div>
        <ProgressBar
          value={match.match_score}
          tone={match.match_score >= 80 ? 'green' : match.match_score >= 60 ? 'blue' : 'amber'}
        />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-400">
          <Droplets className="size-3.5 shrink-0 text-sky-500" />
          {match.water_requirement} water
        </div>
        <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-400">
          <Clock className="size-3.5 shrink-0 text-amber-500" />
          {match.duration_months} months
        </div>
        <div className="col-span-2 flex items-start gap-1.5 text-slate-600 dark:text-slate-400">
          <Sprout className="mt-0.5 size-3.5 shrink-0 text-cane-500" />
          {match.maturity}
        </div>
        <div className="col-span-2 flex items-start gap-1.5 text-slate-600 dark:text-slate-400">
          <Building2 className="mt-0.5 size-3.5 shrink-0 text-slate-400" />
          {match.released_by}
        </div>
      </div>

      <div className="mt-4 flex-1 space-y-3">
        <div>
          <p className="mb-1.5 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-cane-700 dark:text-cane-400">
            <ThumbsUp className="size-3.5" />
            Why it may suit you
          </p>
          <ul className="space-y-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
            {match.why_suitable.map((reason, index) => (
              <li key={index} className="flex gap-1.5">
                <span className="mt-[6px] size-1 shrink-0 rounded-full bg-cane-500" />
                {reason}
              </li>
            ))}
          </ul>
        </div>

        {match.cautions.length > 0 && (
          <div>
            <p className="mb-1.5 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wide text-amber-700 dark:text-amber-400">
              <ShieldAlert className="size-3.5" />
              Cautions
            </p>
            <ul className="space-y-1 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
              {match.cautions.slice(0, 3).map((caution, index) => (
                <li key={index} className="flex gap-1.5">
                  <span className="mt-[6px] size-1 shrink-0 rounded-full bg-amber-500" />
                  {caution}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="mt-4 space-y-2 border-t border-slate-100 pt-3 text-xs dark:border-slate-800">
        <p className="text-slate-600 dark:text-slate-400">
          <span className="font-semibold">Disease notes:</span> {match.disease_notes}
        </p>
        <div className="flex flex-wrap gap-1.5">
          {match.soil_suitability.map((soil) => (
            <span
              key={soil}
              className="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] text-slate-600 dark:bg-slate-800 dark:text-slate-400"
            >
              {soil}
            </span>
          ))}
        </div>
        <p className="text-[11px] italic text-slate-400">{match.source_note}</p>
      </div>
    </div>
  )
}

export default function Varieties() {
  const toast = useToast()
  const [form, setForm] = useState({
    soil_type: 'black' as SoilType,
    region: 'Karnataka',
    district: '',
    climate: 'tropical' as ClimateType,
    irrigation_available: true,
    water_availability: 'medium' as WaterAvailability,
    planting_season: 'general' as PlantingSeason,
    limit: 6,
  })
  const [data, setData] = useState<VarietyRecommendation | null>(null)
  const [loading, setLoading] = useState(false)

  const run = async (payload = form) => {
    setLoading(true)
    try {
      setData(await recommendationApi.variety(payload))
    } catch (caught) {
      toast.error('Could not load recommendations', describeError(caught))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void run()
    // Run once on mount with the default criteria.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    void run()
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-2xl font-extrabold">Variety Guide</h2>
        <p className="mt-1 text-slate-600 dark:text-slate-400">
          Rank sugarcane varieties against your soil, region, climate and water availability.
        </p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,340px)_1fr]">
        <Card className="h-fit">
          <CardHeader title="Your conditions" icon={Search} />
          <form onSubmit={handleSubmit} className="space-y-4 p-5">
            <Field label="Soil type" htmlFor="soil">
              <select
                id="soil"
                className="input"
                value={form.soil_type}
                onChange={(event) => setForm((c) => ({ ...c, soil_type: event.target.value as SoilType }))}
              >
                {SOILS.map((option) => (
                  <option key={option} value={option}>
                    {label(option)}
                  </option>
                ))}
              </select>
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="State / region" htmlFor="region">
                <input
                  id="region"
                  className="input"
                  placeholder="Karnataka"
                  value={form.region}
                  onChange={(event) => setForm((c) => ({ ...c, region: event.target.value }))}
                />
              </Field>
              <Field label="District" htmlFor="district">
                <input
                  id="district"
                  className="input"
                  placeholder="Belagavi"
                  value={form.district}
                  onChange={(event) => setForm((c) => ({ ...c, district: event.target.value }))}
                />
              </Field>
            </div>

            <Field label="Climate" htmlFor="climate">
              <select
                id="climate"
                className="input"
                value={form.climate}
                onChange={(event) => setForm((c) => ({ ...c, climate: event.target.value as ClimateType }))}
              >
                {CLIMATES.map((option) => (
                  <option key={option} value={option}>
                    {label(option)}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Water availability" htmlFor="water">
              <select
                id="water"
                className="input"
                value={form.water_availability}
                onChange={(event) =>
                  setForm((c) => ({ ...c, water_availability: event.target.value as WaterAvailability }))
                }
              >
                {WATER.map((option) => (
                  <option key={option} value={option}>
                    {label(option)}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Planting season" htmlFor="season">
              <select
                id="season"
                className="input"
                value={form.planting_season}
                onChange={(event) =>
                  setForm((c) => ({ ...c, planting_season: event.target.value as PlantingSeason }))
                }
              >
                {SEASONS.map((option) => (
                  <option key={option} value={option}>
                    {label(option)}
                  </option>
                ))}
              </select>
            </Field>

            <label className="flex items-center gap-2.5 text-sm">
              <input
                type="checkbox"
                className="size-4 rounded accent-cane-600"
                checked={form.irrigation_available}
                onChange={(event) =>
                  setForm((c) => ({ ...c, irrigation_available: event.target.checked }))
                }
              />
              Assured irrigation is available
            </label>

            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? <Spinner className="size-4" /> : <Sprout className="size-4" />}
              {loading ? 'Ranking...' : 'Recommend varieties'}
            </button>
          </form>
        </Card>

        <div className="space-y-5">
          {data && (
            <Alert tone="info" title="How the score works" icon={Info}>
              {data.score_explanation}
            </Alert>
          )}

          {loading && !data ? (
            <Card className="grid min-h-[300px] place-items-center">
              <Spinner className="size-8 text-cane-600" />
            </Card>
          ) : !data || data.matches.length === 0 ? (
            <Card>
              <EmptyState
                icon={Sprout}
                title="No varieties matched"
                description="Try widening your criteria, or add entries for your district to data/sugarcane_varieties.json."
              />
            </Card>
          ) : (
            <>
              <div className="grid gap-4 lg:grid-cols-2">
                {data.matches.map((match) => (
                  <VarietyCard key={match.id} match={match} />
                ))}
              </div>

              <Card className="border-amber-200 dark:border-amber-900">
                <div className="flex gap-3 p-5">
                  <CalendarDays className="mt-0.5 size-5 shrink-0 text-amber-600" />
                  <div className="space-y-2 text-sm">
                    <p className="font-semibold text-slate-800 dark:text-slate-200">
                      Before you buy seed cane
                    </p>
                    <p className="leading-relaxed text-slate-600 dark:text-slate-400">
                      {data.disclaimer}
                    </p>
                    <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                      {data.data_disclaimer}
                    </p>
                    <p className="text-xs text-slate-400">
                      Knowledge base last reviewed {data.last_reviewed} | {data.considered} varieties
                      considered. Edit <code>data/sugarcane_varieties.json</code> to add your own.
                    </p>
                  </div>
                </div>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
