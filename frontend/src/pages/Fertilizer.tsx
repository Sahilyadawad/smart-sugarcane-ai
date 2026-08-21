import { useEffect, useState, type FormEvent } from 'react'
import {
  Beaker,
  CalendarRange,
  CheckCircle2,
  FlaskConical,
  Layers,
  Leaf,
  Sprout,
  TriangleAlert,
} from 'lucide-react'
import {
  Alert,
  Badge,
  BulletList,
  Card,
  CardHeader,
  Disclaimer,
  Field,
  Spinner,
} from '../components/ui'
import { useToast } from '../context/ToastContext'
import { describeError } from '../services/api'
import { recommendationApi } from '../services/endpoints'
import { label } from '../utils/format'
import type {
  FertilizerRecommendation,
  GrowthStage,
  SoilType,
  WaterAvailability,
} from '../types'

const STAGES: GrowthStage[] = [
  'germination',
  'tillering',
  'grand_growth',
  'maturation',
  'ratoon_initiation',
]
const SOILS: SoilType[] = ['black', 'red', 'sandy', 'clay', 'loamy', 'mixed']
const WATER: WaterAvailability[] = ['low', 'medium', 'high']

const PRIORITY_STYLE: Record<string, string> = {
  high: 'border-red-300 bg-red-100 text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-200',
  medium:
    'border-amber-300 bg-amber-100 text-amber-900 dark:border-amber-900 dark:bg-amber-950 dark:text-amber-200',
  low: 'border-cane-300 bg-cane-100 text-cane-900 dark:border-cane-900 dark:bg-cane-950 dark:text-cane-200',
}

const NUTRIENT_ICON: Record<string, string> = {
  Nitrogen: 'N',
  Phosphorus: 'P',
  Potassium: 'K',
}

/** Shared by this page and the Soil Analysis page. */
export function FertilizerPanel({ data }: { data: FertilizerRecommendation }) {
  return (
    <div className="space-y-6">
      <div className="rounded-2xl bg-gradient-to-br from-cane-50 to-white p-5 dark:from-cane-950/50 dark:to-slate-900">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Current growth stage
            </p>
            <h4 className="mt-1 font-display text-xl font-extrabold">{data.growth_stage_label}</h4>
            <p className="mt-0.5 text-sm text-slate-500">{data.typical_window}</p>
          </div>
          {data.lab_values_used && (
            <Badge className="border-sky-300 bg-sky-100 text-sky-900 dark:border-sky-800 dark:bg-sky-950 dark:text-sky-200">
              <Beaker className="size-3.5" />
              Using your lab values
            </Badge>
          )}
        </div>
        <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
          {data.stage_goal} {data.stage_focus}
        </p>
      </div>

      {/* Nutrient focus */}
      <div>
        <h4 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-500">Nutrient focus</h4>
        <div className="grid gap-3 sm:grid-cols-3">
          {data.nutrient_focus.map((nutrient) => (
            <div
              key={nutrient.nutrient}
              className="rounded-xl border border-slate-200 p-4 dark:border-slate-800"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="grid size-9 place-items-center rounded-lg bg-slate-100 font-display text-base font-extrabold text-slate-700 dark:bg-slate-800 dark:text-slate-200">
                  {NUTRIENT_ICON[nutrient.nutrient] ?? nutrient.nutrient[0]}
                </span>
                <Badge className={PRIORITY_STYLE[nutrient.priority]}>
                  {nutrient.priority} priority
                </Badge>
              </div>
              <p className="mt-3 text-sm font-bold">{nutrient.nutrient}</p>
              {nutrient.lab_rating && (
                <p className="mt-0.5 text-xs font-medium text-sky-700 dark:text-sky-400">
                  Soil test rating: {nutrient.lab_rating}
                </p>
              )}
              <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                {nutrient.reason}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Split schedule */}
      {data.split_schedule.length > 0 && (
        <div>
          <h4 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-slate-500">
            <CalendarRange className="size-4" />
            Split application schedule
          </h4>
          <div className="space-y-2">
            {data.split_schedule.map((entry) => (
              <div
                key={entry.stage}
                className={`rounded-xl border p-4 transition ${
                  entry.is_current
                    ? 'border-cane-400 bg-cane-50 dark:border-cane-700 dark:bg-cane-950/50'
                    : entry.is_past
                      ? 'border-slate-200 bg-slate-50 opacity-70 dark:border-slate-800 dark:bg-slate-900/50'
                      : 'border-slate-200 dark:border-slate-800'
                }`}
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    {entry.is_current ? (
                      <CheckCircle2 className="size-4 text-cane-600" />
                    ) : (
                      <span className="size-4 rounded-full border-2 border-slate-300 dark:border-slate-600" />
                    )}
                    <p className="text-sm font-bold">{entry.label}</p>
                    {entry.is_current && (
                      <Badge className="border-cane-300 bg-cane-200 text-cane-900 dark:border-cane-700 dark:bg-cane-900 dark:text-cane-100">
                        You are here
                      </Badge>
                    )}
                  </div>
                  <div className="flex gap-1.5">
                    {Object.entries(entry.nutrient_priority).map(([nutrient, priority]) => (
                      <span
                        key={nutrient}
                        className={`rounded-md border px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                          PRIORITY_STYLE[priority as string] ?? PRIORITY_STYLE.low
                        }`}
                        title={`${nutrient}: ${priority} priority`}
                      >
                        {NUTRIENT_ICON[nutrient[0].toUpperCase() + nutrient.slice(1)] ??
                          nutrient[0].toUpperCase()}
                      </span>
                    ))}
                  </div>
                </div>
                <p className="mt-1.5 text-xs text-slate-500">{entry.window}</p>
                {entry.is_current && (
                  <p className="mt-2 text-xs leading-relaxed text-slate-600 dark:text-slate-400">
                    {entry.timing_note}
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <div>
          <h4 className="mb-3 text-sm font-bold uppercase tracking-wide text-slate-500">
            Suggested management
          </h4>
          <BulletList items={data.suggested_management} tone="success" />
        </div>
        <div className="space-y-4">
          <div>
            <h4 className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-500">
              Organic matter
            </h4>
            <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
              {data.organic_matter_advice}
            </p>
          </div>
          <div>
            <h4 className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-500">
              Water availability
            </h4>
            <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">{data.water_note}</p>
          </div>
          {data.ph_note && (
            <Alert tone="info" title="Soil pH">
              {data.ph_note}
            </Alert>
          )}
          {data.plant_health_note && (
            <div>
              <h4 className="mb-2 text-sm font-bold uppercase tracking-wide text-slate-500">
                Crop health
              </h4>
              <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                {data.plant_health_note}
              </p>
            </div>
          )}
        </div>
      </div>

      {data.soil_specific_notes.length > 0 && (
        <div>
          <h4 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-slate-500">
            <Layers className="size-4" />
            About your soil
          </h4>
          <BulletList items={data.soil_specific_notes} />
        </div>
      )}

      <Disclaimer>{data.disclaimer}</Disclaimer>
    </div>
  )
}

export default function Fertilizer() {
  const toast = useToast()
  const [form, setForm] = useState({
    growth_stage: 'grand_growth' as GrowthStage,
    soil_type: 'black' as SoilType,
    water_availability: 'medium' as WaterAvailability,
    irrigation_available: true,
    nitrogen_kg_ha: '',
    phosphorus_kg_ha: '',
    potassium_kg_ha: '',
    soil_ph: '',
  })
  const [data, setData] = useState<FertilizerRecommendation | null>(null)
  const [loading, setLoading] = useState(false)

  const run = async () => {
    setLoading(true)
    try {
      const toNumber = (value: string) => (value.trim() === '' ? null : Number(value))
      setData(
        await recommendationApi.fertilizer({
          growth_stage: form.growth_stage,
          soil_type: form.soil_type,
          water_availability: form.water_availability,
          irrigation_available: form.irrigation_available,
          nitrogen_kg_ha: toNumber(form.nitrogen_kg_ha),
          phosphorus_kg_ha: toNumber(form.phosphorus_kg_ha),
          potassium_kg_ha: toNumber(form.potassium_kg_ha),
          soil_ph: toNumber(form.soil_ph),
        }),
      )
    } catch (caught) {
      toast.error('Could not load guidance', describeError(caught))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    void run()
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-2xl font-extrabold">Fertilizer Guidance</h2>
        <p className="mt-1 text-slate-600 dark:text-slate-400">
          Stage-based nutrient priorities and split timing for your soil.
        </p>
      </div>

      <Alert tone="warning" title="This engine does not give dosages" icon={TriangleAlert}>
        It tells you <strong>which nutrients matter now</strong> and <strong>how to time them</strong>,
        not how many kilograms to apply. A safe quantity depends on your soil test, your variety, your
        yield target and your state recommendation - none of which can be inferred from a form. Get the
        quantities from a laboratory soil test and your local agricultural extension office.
      </Alert>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,340px)_1fr]">
        <Card className="h-fit">
          <CardHeader title="Your crop and soil" icon={Sprout} />
          <form onSubmit={handleSubmit} className="space-y-4 p-5">
            <Field label="Growth stage" htmlFor="stage">
              <select
                id="stage"
                className="input"
                value={form.growth_stage}
                onChange={(event) =>
                  setForm((c) => ({ ...c, growth_stage: event.target.value as GrowthStage }))
                }
              >
                {STAGES.map((option) => (
                  <option key={option} value={option}>
                    {label(option)}
                  </option>
                ))}
              </select>
            </Field>

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

            <div className="rounded-xl border border-dashed border-slate-300 p-4 dark:border-slate-700">
              <h4 className="flex items-center gap-2 text-sm font-bold">
                <Beaker className="size-4 text-sky-600" />
                Soil test values (optional)
              </h4>
              <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                From your soil health card, in kg/ha. Supplying these lets the engine raise or lower
                each nutrient's priority instead of relying on the growth stage alone.
              </p>
              <div className="mt-3 space-y-3">
                <div className="grid grid-cols-3 gap-2">
                  <Field label="N" htmlFor="n">
                    <input
                      id="n"
                      type="number"
                      min={0}
                      className="input px-2"
                      placeholder="280"
                      value={form.nitrogen_kg_ha}
                      onChange={(event) => setForm((c) => ({ ...c, nitrogen_kg_ha: event.target.value }))}
                    />
                  </Field>
                  <Field label="P" htmlFor="p">
                    <input
                      id="p"
                      type="number"
                      min={0}
                      className="input px-2"
                      placeholder="18"
                      value={form.phosphorus_kg_ha}
                      onChange={(event) =>
                        setForm((c) => ({ ...c, phosphorus_kg_ha: event.target.value }))
                      }
                    />
                  </Field>
                  <Field label="K" htmlFor="k">
                    <input
                      id="k"
                      type="number"
                      min={0}
                      className="input px-2"
                      placeholder="180"
                      value={form.potassium_kg_ha}
                      onChange={(event) =>
                        setForm((c) => ({ ...c, potassium_kg_ha: event.target.value }))
                      }
                    />
                  </Field>
                </div>
                <Field label="Soil pH" htmlFor="ph">
                  <input
                    id="ph"
                    type="number"
                    step="0.1"
                    min={0}
                    max={14}
                    className="input"
                    placeholder="7.2"
                    value={form.soil_ph}
                    onChange={(event) => setForm((c) => ({ ...c, soil_ph: event.target.value }))}
                  />
                </Field>
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? <Spinner className="size-4" /> : <FlaskConical className="size-4" />}
              {loading ? 'Working it out...' : 'Get fertilizer guidance'}
            </button>
          </form>
        </Card>

        <Card>
          <CardHeader
            title="Fertilizer recommendation"
            subtitle="Qualitative priorities and timing, no dosages"
            icon={Leaf}
          />
          <div className="p-5">
            {loading && !data ? (
              <div className="grid min-h-[300px] place-items-center">
                <Spinner className="size-8 text-cane-600" />
              </div>
            ) : data ? (
              <FertilizerPanel data={data} />
            ) : (
              <p className="py-12 text-center text-sm text-slate-500">
                Choose your growth stage and soil type, then press the button.
              </p>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}
