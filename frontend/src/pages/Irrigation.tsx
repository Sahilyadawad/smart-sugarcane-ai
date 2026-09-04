import { useCallback, useEffect, useState, type FormEvent } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  CloudRain,
  Droplets,
  Gauge,
  Info,
  Lightbulb,
  RefreshCw,
  Sparkles,
  Thermometer,
  Timer,
  Wind,
} from 'lucide-react'
import {
  Alert,
  BulletList,
  Card,
  CardHeader,
  Disclaimer,
  Field,
  ProgressBar,
  Spinner,
  StatCard,
} from '../components/ui'
import { ModelBadge } from '../components/ModelBadge'
import { HonestyNotice } from '../components/HonestyNotice'
import { useToast } from '../context/ToastContext'
import { describeError } from '../services/api'
import { irrigationApi, weatherApi } from '../services/endpoints'
import {
  PRIORITY_TONE,
  formatDuration,
  formatLitres,
  formatNumber,
  label,
} from '../utils/format'
import type {
  GrowthStage,
  IrrigationChartPoint,
  IrrigationInput,
  IrrigationModelStatus,
  IrrigationResult,
  IrrigationMethod,
  SoilType,
  WeatherCondition,
} from '../types'

const SOIL_TYPES: SoilType[] = ['alluvial', 'black', 'red', 'sandy', 'clay', 'loamy', 'mixed']
const GROWTH_STAGES: GrowthStage[] = [
  'germination',
  'tillering',
  'grand_growth',
  'maturation',
  'ratoon_initiation',
]
const WEATHER: WeatherCondition[] = [
  'clear',
  'partly_cloudy',
  'cloudy',
  'rainy',
  'stormy',
  'humid',
  'dry_wind',
]
const METHODS: IrrigationMethod[] = ['flood', 'furrow', 'sprinkler', 'drip']

const DEFAULTS: IrrigationInput = {
  soil_moisture: 40,
  temperature: 32,
  humidity: 55,
  rainfall: 0,
  rain_probability: 10,
  wind_speed: 8,
  weather_condition: 'clear',
  soil_type: 'black',
  growth_stage: 'grand_growth',
  irrigation_method: 'furrow',
  area_hectares: 1,
  save: true,
}

export default function Irrigation() {
  const toast = useToast()
  const [form, setForm] = useState<IrrigationInput>(DEFAULTS)
  const [result, setResult] = useState<IrrigationResult | null>(null)
  const [chart, setChart] = useState<IrrigationChartPoint[]>([])
  const [modelStatus, setModelStatus] = useState<IrrigationModelStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [weatherLoading, setWeatherLoading] = useState(false)
  const [simulating, setSimulating] = useState(false)
  const [daysSince, setDaysSince] = useState(4)

  const set = <K extends keyof IrrigationInput>(key: K, value: IrrigationInput[K]) =>
    setForm((current) => ({ ...current, [key]: value }))

  const loadChart = useCallback(async () => {
    try {
      setChart(await irrigationApi.chart(10))
    } catch {
      // A missing chart is not worth interrupting the user for.
    }
  }, [])

  useEffect(() => {
    void loadChart()
    irrigationApi.modelStatus().then(setModelStatus).catch(() => setModelStatus(null))
  }, [loadChart])

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setLoading(true)
    try {
      const data = await irrigationApi.predict(form)
      setResult(data)
      toast.success(
        data.irrigation_required ? 'Irrigation recommended' : 'No irrigation needed',
        data.irrigation_required
          ? `${formatNumber(data.water_requirement_mm)} mm, ${data.priority} priority`
          : data.soil_moisture_status,
      )
      void loadChart()
      requestAnimationFrame(() =>
        document.getElementById('irrigation-result')?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
      )
    } catch (caught) {
      toast.error('Prediction failed', describeError(caught))
    } finally {
      setLoading(false)
    }
  }

  const handleWeather = async () => {
    setWeatherLoading(true)
    try {
      const data = await weatherApi.prefill()
      if (!data.available || !data.values) {
        toast.info('Live weather not configured', data.notice ?? data.reason ?? '')
        return
      }
      setForm((current) => ({ ...current, ...data.values }))
      toast.success(`Weather loaded for ${data.city}`, data.not_filled_note ?? '')
    } catch (caught) {
      toast.error('Could not fetch weather', describeError(caught))
    } finally {
      setWeatherLoading(false)
    }
  }

  const handleSimulate = async () => {
    setSimulating(true)
    try {
      const data = await irrigationApi.simulateSoilMoisture({
        days_since_irrigation: daysSince,
        starting_moisture: 88,
        soil_type: form.soil_type,
        growth_stage: form.growth_stage,
        temperature: form.temperature,
        humidity: form.humidity,
        wind_speed: form.wind_speed,
        weather_condition: form.weather_condition,
        rainfall_since: form.rainfall,
      })
      const value = Number(data.simulated_soil_moisture)
      set('soil_moisture', value)
      toast.info(
        `Simulated soil moisture: ${value}%`,
        `Water balance: crop uses about ${data.daily_crop_water_use_mm} mm/day, root zone holds about ${data.root_zone_available_water_mm} mm. Confirm by hand before acting on it.`,
      )
    } catch (caught) {
      toast.error('Simulation failed', describeError(caught))
    } finally {
      setSimulating(false)
    }
  }

  const contributionData =
    result?.feature_contributions.map((item) => ({
      name: item.label,
      impact: item.impact,
      note: item.note,
    })) ?? []

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-2xl font-extrabold">Smart Irrigation</h2>
        <p className="mt-1 text-slate-600 dark:text-slate-400">
          Enter the field conditions to get a water requirement, a duration and a priority - with the
          calculation shown.
        </p>
      </div>

      {modelStatus && (
        <HonestyNotice
          source={modelStatus.trained_model_available ? 'trained_model' : 'rule_engine'}
          summary={
            modelStatus.trained_model_available
              ? 'Random Forest trained on a synthetic water-balance dataset.'
              : 'Transparent water-balance calculation. Run ml/irrigation/train.py to enable the ML model.'
          }
          notes={modelStatus.notes}
        />
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,420px)_1fr]">
        {/* ---------------------------------------------------------- inputs */}
        <Card>
          <CardHeader
            title="Field conditions"
            subtitle="Soil, weather and crop stage"
            icon={Gauge}
            action={
              <button
                type="button"
                onClick={handleWeather}
                disabled={weatherLoading}
                className="btn-secondary shrink-0 px-3 py-1.5 text-xs"
              >
                {weatherLoading ? <Spinner className="size-3.5" /> : <CloudRain className="size-3.5" />}
                Use weather
              </button>
            }
          />

          <form onSubmit={handleSubmit} className="space-y-5 p-5">
            {/* Soil moisture */}
            <div>
              <div className="mb-2 flex items-baseline justify-between">
                <label htmlFor="soil-moisture" className="text-sm font-medium">
                  Soil moisture
                </label>
                <span className="font-display text-lg font-extrabold text-cane-600">
                  {form.soil_moisture}%
                </span>
              </div>
              <input
                id="soil-moisture"
                type="range"
                min={0}
                max={100}
                step={1}
                value={form.soil_moisture}
                onChange={(event) => set('soil_moisture', Number(event.target.value))}
                className="w-full accent-cane-600"
              />
              <div className="mt-1 flex justify-between text-[11px] text-slate-400">
                <span>0 Dry</span>
                <span>50</span>
                <span>100 Saturated</span>
              </div>

              <div className="mt-3 flex items-end gap-2 rounded-xl border border-dashed border-slate-300 p-3 dark:border-slate-700">
                <div className="flex-1">
                  <label htmlFor="days-since" className="text-xs font-medium text-slate-600 dark:text-slate-400">
                    No sensor? Days since last irrigation
                  </label>
                  <input
                    id="days-since"
                    type="number"
                    min={0}
                    max={60}
                    value={daysSince}
                    onChange={(event) => setDaysSince(Number(event.target.value))}
                    className="input mt-1 py-1.5 text-sm"
                  />
                </div>
                <button
                  type="button"
                  onClick={handleSimulate}
                  disabled={simulating}
                  className="btn-secondary shrink-0 px-3 py-2 text-xs"
                >
                  {simulating ? <Spinner className="size-3.5" /> : <Sparkles className="size-3.5" />}
                  Simulate
                </button>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Field label="Temperature (C)" htmlFor="temperature">
                <input
                  id="temperature"
                  type="number"
                  step="0.1"
                  min={-10}
                  max={60}
                  required
                  className="input"
                  value={form.temperature}
                  onChange={(event) => set('temperature', Number(event.target.value))}
                />
              </Field>
              <Field label="Humidity (%)" htmlFor="humidity">
                <input
                  id="humidity"
                  type="number"
                  step="1"
                  min={0}
                  max={100}
                  required
                  className="input"
                  value={form.humidity}
                  onChange={(event) => set('humidity', Number(event.target.value))}
                />
              </Field>
              <Field label="Rainfall, last 24 h (mm)" htmlFor="rainfall">
                <input
                  id="rainfall"
                  type="number"
                  step="0.1"
                  min={0}
                  max={500}
                  className="input"
                  value={form.rainfall}
                  onChange={(event) => set('rainfall', Number(event.target.value))}
                />
              </Field>
              <Field label="Rain chance, next 24 h (%)" htmlFor="rain-probability">
                <input
                  id="rain-probability"
                  type="number"
                  step="1"
                  min={0}
                  max={100}
                  className="input"
                  value={form.rain_probability}
                  onChange={(event) => set('rain_probability', Number(event.target.value))}
                />
              </Field>
              <Field label="Wind speed (km/h)" htmlFor="wind">
                <input
                  id="wind"
                  type="number"
                  step="0.1"
                  min={0}
                  max={150}
                  className="input"
                  value={form.wind_speed}
                  onChange={(event) => set('wind_speed', Number(event.target.value))}
                />
              </Field>
              <Field label="Area (hectares)" htmlFor="area">
                <input
                  id="area"
                  type="number"
                  step="0.1"
                  min={0.1}
                  max={1000}
                  className="input"
                  value={form.area_hectares}
                  onChange={(event) => set('area_hectares', Number(event.target.value))}
                />
              </Field>
            </div>

            <Field label="Weather condition" htmlFor="weather">
              <select
                id="weather"
                className="input"
                value={form.weather_condition}
                onChange={(event) => set('weather_condition', event.target.value as WeatherCondition)}
              >
                {WEATHER.map((option) => (
                  <option key={option} value={option}>
                    {label(option)}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Soil type" htmlFor="soil-type">
              <select
                id="soil-type"
                className="input"
                value={form.soil_type}
                onChange={(event) => set('soil_type', event.target.value as SoilType)}
              >
                {SOIL_TYPES.map((option) => (
                  <option key={option} value={option}>
                    {label(option)}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Growth stage" htmlFor="growth-stage">
              <select
                id="growth-stage"
                className="input"
                value={form.growth_stage}
                onChange={(event) => set('growth_stage', event.target.value as GrowthStage)}
              >
                {GROWTH_STAGES.map((option) => (
                  <option key={option} value={option}>
                    {label(option)}
                  </option>
                ))}
              </select>
            </Field>

            <Field
              label="Irrigation method"
              htmlFor="method"
              hint="Sets the application efficiency and how long irrigation should run."
            >
              <select
                id="method"
                className="input"
                value={form.irrigation_method}
                onChange={(event) => set('irrigation_method', event.target.value as IrrigationMethod)}
              >
                {METHODS.map((option) => (
                  <option key={option} value={option}>
                    {label(option)}
                  </option>
                ))}
              </select>
            </Field>

            <div className="flex gap-2 pt-1">
              <button type="submit" disabled={loading} className="btn-primary flex-1">
                {loading ? <Spinner className="size-4" /> : <Droplets className="size-4" />}
                {loading ? 'Analysing...' : 'Get AI Recommendation'}
              </button>
              <button
                type="button"
                onClick={() => {
                  setForm(DEFAULTS)
                  setResult(null)
                }}
                className="btn-secondary px-3"
                aria-label="Reset the form"
              >
                <RefreshCw className="size-4" />
              </button>
            </div>
          </form>
        </Card>

        {/* --------------------------------------------------------- results */}
        <div className="space-y-6" id="irrigation-result">
          {!result ? (
            <Card className="grid min-h-[420px] place-items-center p-8 text-center">
              <div>
                <span className="mx-auto grid size-16 place-items-center rounded-2xl bg-sky-50 text-sky-500 dark:bg-sky-950 dark:text-sky-400">
                  <Droplets className="size-8" />
                </span>
                <h3 className="mt-5 text-lg font-bold">No recommendation yet</h3>
                <p className="mx-auto mt-2 max-w-sm text-sm text-slate-500 dark:text-slate-400">
                  Fill in the field conditions and press{' '}
                  <strong>Get AI Recommendation</strong>. If you do not have a soil moisture sensor,
                  use the simulator to estimate it from a water balance.
                </p>
              </div>
            </Card>
          ) : (
            <>
              {/* Headline */}
              <Card
                className={`overflow-hidden border-2 ${
                  result.irrigation_required
                    ? 'border-cane-300 dark:border-cane-800'
                    : 'border-slate-200 dark:border-slate-800'
                }`}
              >
                <div
                  className={`p-6 ${
                    result.irrigation_required
                      ? 'bg-gradient-to-br from-cane-50 to-white dark:from-cane-950/60 dark:to-slate-900'
                      : 'bg-slate-50 dark:bg-slate-900'
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                        Irrigation Required
                      </p>
                      <p className="mt-1 font-display text-4xl font-extrabold">
                        {result.irrigation_required ? 'YES' : 'NO'}
                      </p>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <span
                        className={`rounded-full border px-3 py-1 text-xs font-bold uppercase tracking-wide ${
                          PRIORITY_TONE[result.priority]
                        }`}
                      >
                        {result.priority} priority
                      </span>
                      <ModelBadge source={result.model_source} />
                    </div>
                  </div>

                  <p className="mt-4 leading-relaxed text-slate-700 dark:text-slate-300">
                    {result.reason}
                  </p>

                  {result.irrigation_required && (
                    <div className="mt-6 grid gap-3 sm:grid-cols-3">
                      <div className="rounded-xl bg-white p-4 shadow-sm dark:bg-slate-800">
                        <p className="text-xs font-medium text-slate-500">Recommended water</p>
                        <p className="mt-1 font-display text-2xl font-extrabold text-sky-600">
                          {formatNumber(result.water_requirement_mm)}
                          <span className="ml-1 text-sm">mm</span>
                        </p>
                        <p className="mt-0.5 text-xs text-slate-500">
                          {formatLitres(result.water_volume_liters)} total
                        </p>
                      </div>
                      <div className="rounded-xl bg-white p-4 shadow-sm dark:bg-slate-800">
                        <p className="text-xs font-medium text-slate-500">Duration</p>
                        <p className="mt-1 font-display text-2xl font-extrabold text-cane-600">
                          {formatDuration(result.duration_minutes)}
                        </p>
                        <p className="mt-0.5 text-xs text-slate-500">
                          {label(form.irrigation_method)}
                        </p>
                      </div>
                      <div className="rounded-xl bg-white p-4 shadow-sm dark:bg-slate-800">
                        <p className="text-xs font-medium text-slate-500">Next check</p>
                        <p className="mt-1 font-display text-2xl font-extrabold text-amber-600">
                          {result.next_check_hours}
                          <span className="ml-1 text-sm">h</span>
                        </p>
                        <p className="mt-0.5 text-xs text-slate-500">from now</p>
                      </div>
                    </div>
                  )}

                  <div className="mt-5 space-y-2 text-sm">
                    <p className="flex items-start gap-2 text-slate-600 dark:text-slate-400">
                      <Timer className="mt-0.5 size-4 shrink-0 text-slate-400" />
                      <span>
                        <strong className="font-semibold text-slate-700 dark:text-slate-300">
                          Best time:
                        </strong>{' '}
                        {result.recommended_window}
                      </span>
                    </p>
                    <p className="flex items-start gap-2 text-slate-600 dark:text-slate-400">
                      <CloudRain className="mt-0.5 size-4 shrink-0 text-slate-400" />
                      <span>
                        <strong className="font-semibold text-slate-700 dark:text-slate-300">
                          Rain forecast:
                        </strong>{' '}
                        {result.rain_forecast_note}
                      </span>
                    </p>
                    <p className="flex items-start gap-2 text-slate-600 dark:text-slate-400">
                      <Gauge className="mt-0.5 size-4 shrink-0 text-slate-400" />
                      <span>
                        <strong className="font-semibold text-slate-700 dark:text-slate-300">
                          Soil moisture:
                        </strong>{' '}
                        {result.soil_moisture_status}
                      </span>
                    </p>
                  </div>
                </div>
              </Card>

              {/* Water balance */}
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <StatCard
                  label="Root zone deficit"
                  value={formatNumber(result.deficit_mm)}
                  unit="mm"
                  icon={Droplets}
                  tone="blue"
                />
                <StatCard
                  label="Crop water use"
                  value={formatNumber(result.crop_water_use_mm)}
                  unit="mm/day"
                  icon={Thermometer}
                  tone="amber"
                  hint={`Kc ${formatNumber(result.crop_coefficient, 2)}`}
                />
                <StatCard
                  label="Reference ET"
                  value={formatNumber(result.reference_et_mm)}
                  unit="mm/day"
                  icon={Wind}
                  tone="default"
                />
                <StatCard
                  label="Effective rainfall"
                  value={formatNumber(result.effective_rain_mm)}
                  unit="mm"
                  icon={CloudRain}
                  tone="green"
                />
              </div>

              {/* Contributions chart */}
              <Card>
                <CardHeader
                  title="What drove this result"
                  subtitle="Signed effect of each factor on the water requirement, in mm"
                  icon={Gauge}
                />
                <div className="p-5">
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={contributionData} layout="vertical" margin={{ left: 20, right: 20 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-slate-200 dark:text-slate-800" />
                        <XAxis type="number" tick={{ fontSize: 11 }} />
                        <YAxis type="category" dataKey="name" width={130} tick={{ fontSize: 11 }} />
                        <Tooltip
                          formatter={(value: number) => [`${value.toFixed(2)} mm`, 'Effect']}
                          contentStyle={{ borderRadius: 12, fontSize: 12 }}
                        />
                        <Bar dataKey="impact" radius={[0, 6, 6, 0]}>
                          {contributionData.map((entry, index) => (
                            <Cell key={index} fill={entry.impact >= 0 ? '#0ea5e9' : '#22c55e'} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                  <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
                    Blue bars increase the water requirement, green bars reduce it.
                  </p>
                </div>
              </Card>

              {/* Explanation */}
              <div className="grid gap-6 lg:grid-cols-2">
                <Card>
                  <CardHeader title="How this was worked out" icon={Info} />
                  <div className="p-5">
                    <BulletList items={result.explanation} />
                  </div>
                </Card>

                <Card>
                  <CardHeader title="Water saving tips" icon={Lightbulb} />
                  <div className="p-5">
                    <BulletList items={result.water_saving_tips} tone="success" />
                  </div>
                </Card>
              </div>

              <Disclaimer>{result.disclaimer}</Disclaimer>

              {result.model_notes.length > 0 && (
                <Alert tone="info" title="Model notes">
                  <ul className="list-disc space-y-1 pl-4">
                    {result.model_notes.map((note, index) => (
                      <li key={index}>{note}</li>
                    ))}
                  </ul>
                </Alert>
              )}
            </>
          )}

          {/* History chart */}
          {chart.length > 1 && (
            <Card>
              <CardHeader
                title="Your irrigation history"
                subtitle="Soil moisture and water applied over your last checks"
                icon={Droplets}
              />
              <div className="h-72 p-5">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chart}>
                    <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-slate-200 dark:text-slate-800" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis yAxisId="left" tick={{ fontSize: 11 }} label={{ value: '%', angle: -90, position: 'insideLeft', fontSize: 11 }} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} label={{ value: 'mm', angle: 90, position: 'insideRight', fontSize: 11 }} />
                    <Tooltip contentStyle={{ borderRadius: 12, fontSize: 12 }} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    <Line yAxisId="left" type="monotone" dataKey="soil_moisture" name="Soil moisture (%)" stroke="#0ea5e9" strokeWidth={2} dot={{ r: 3 }} />
                    <Line yAxisId="left" type="monotone" dataKey="temperature" name="Temperature (C)" stroke="#f59e0b" strokeWidth={2} dot={{ r: 3 }} />
                    <Line yAxisId="right" type="monotone" dataKey="water_mm" name="Water needed (mm)" stroke="#16a34a" strokeWidth={2} dot={{ r: 3 }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>
          )}
        </div>
      </div>

      {/* Moisture reference */}
      <Card>
        <CardHeader title="Reading soil moisture" subtitle="What the percentages mean for sugarcane" icon={Gauge} />
        <div className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-5">
          {[
            { range: 'Above 70%', tone: 'green' as const, value: 85, text: 'Plenty of moisture. Check water is not standing.' },
            { range: '50 - 70%', tone: 'green' as const, value: 60, text: 'Comfortable for most growth stages.' },
            { range: '35 - 50%', tone: 'blue' as const, value: 42, text: 'Drawing down reserves. Irrigation usually due soon.' },
            { range: '20 - 35%', tone: 'amber' as const, value: 27, text: 'Visible stress likely: rolled leaves, slowed growth.' },
            { range: 'Below 20%', tone: 'red' as const, value: 12, text: 'Critical. Grand growth losses are hard to recover.' },
          ].map((band) => (
            <div key={band.range} className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
              <p className="text-sm font-bold">{band.range}</p>
              <div className="my-2">
                <ProgressBar value={band.value} tone={band.tone} />
              </div>
              <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">{band.text}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
