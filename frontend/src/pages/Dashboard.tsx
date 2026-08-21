import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Activity,
  ArrowRight,
  Bot,
  Cloud,
  Droplets,
  FlaskConical,
  History,
  Leaf,
  Lightbulb,
  Mountain,
  Sprout,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'
import {
  Alert,
  Badge,
  Card,
  CardHeader,
  SkeletonCard,
  StatCard,
} from '../components/ui'
import { ModelBadge } from '../components/ModelBadge'
import { useAuth } from '../context/AuthContext'
import { describeError, mediaUrl } from '../services/api'
import { dashboardApi } from '../services/endpoints'
import { PRIORITY_TONE, formatDate, formatNumber, label, percent, relativeTime } from '../utils/format'
import type { DashboardSummary, ModelSource } from '../types'

const QUICK_ACTIONS = [
  { to: '/plant-analysis', label: 'Plant Health', icon: Leaf, tone: 'bg-cane-600' },
  { to: '/irrigation', label: 'Irrigation', icon: Droplets, tone: 'bg-sky-600' },
  { to: '/soil-analysis', label: 'Soil Analysis', icon: Mountain, tone: 'bg-soil-600' },
  { to: '/varieties', label: 'Variety Guide', icon: Sprout, tone: 'bg-emerald-600' },
  { to: '/fertilizer', label: 'Fertilizer', icon: FlaskConical, tone: 'bg-violet-600' },
  { to: '/assistant', label: 'AI Assistant', icon: Bot, tone: 'bg-amber-600' },
]

interface LatestPlant {
  id: number
  condition_label: string
  confidence: number
  severity: string
  health_score: number
  image_url: string
  is_demo: boolean
  created_at: string
}
interface LatestSoil {
  id: number
  soil_label: string
  confidence: number
  moisture_appearance: string
  image_url: string
  created_at: string
}
interface LatestIrrigation {
  irrigation_required: boolean
  priority: string
  water_requirement_mm: number
  duration_minutes: number
  soil_moisture: number
  temperature: number
  reason: string
  model_source: ModelSource
  created_at: string
}

export default function Dashboard() {
  const { user } = useAuth()
  const [data, setData] = useState<DashboardSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    dashboardApi
      .summary()
      .then(setData)
      .catch((caught) => setError(describeError(caught)))
  }, [])

  if (error) {
    return (
      <Alert tone="danger" title="Could not load your dashboard">
        {error}
      </Alert>
    )
  }

  if (!data) {
    return (
      <div className="space-y-6">
        <div className="skeleton h-9 w-64" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((index) => (
            <SkeletonCard key={index} />
          ))}
        </div>
        <div className="grid gap-6 lg:grid-cols-3">
          {[0, 1, 2].map((index) => (
            <div key={index} className="skeleton h-64" />
          ))}
        </div>
      </div>
    )
  }

  const plant = data.latest_plant as unknown as LatestPlant | null
  const soil = data.latest_soil as unknown as LatestSoil | null
  const irrigation = data.latest_irrigation as unknown as LatestIrrigation | null
  const weather = (data.weather ?? {}) as Record<string, unknown>
  const trendDirection = data.plant_trend?.direction ?? 'insufficient_data'
  const TrendIcon =
    trendDirection === 'improving' ? TrendingUp : trendDirection === 'deteriorating' ? TrendingDown : Activity

  return (
    <div className="space-y-6">
      {/* Greeting */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h2 className="font-display text-2xl font-extrabold">{data.greeting}</h2>
          <p className="mt-1 text-slate-600 dark:text-slate-400">
            {data.totals.total > 0
              ? `You have ${data.totals.total} saved ${data.totals.total === 1 ? 'analysis' : 'analyses'}.`
              : 'Run your first irrigation check or upload a plant photo to get started.'}
          </p>
        </div>
        {user?.farm_location && (
          <Badge className="border-slate-200 bg-white text-slate-600 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300">
            <Mountain className="size-3.5" />
            {user.farm_location}
          </Badge>
        )}
      </div>

      {/* Weather */}
      {weather.available ? (
        <Card className="overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-4 bg-gradient-to-r from-sky-50 to-white p-5 dark:from-sky-950/40 dark:to-slate-900">
            <div className="flex items-center gap-4">
              <span className="grid size-12 place-items-center rounded-2xl bg-sky-100 text-sky-600 dark:bg-sky-900 dark:text-sky-300">
                <Cloud className="size-6" />
              </span>
              <div>
                <p className="font-display text-xl font-extrabold">{String(weather.headline)}</p>
                <p className="text-sm text-slate-500 dark:text-slate-400">{String(weather.detail)}</p>
              </div>
            </div>
            <Link to="/irrigation" className="btn-secondary text-xs">
              Use in irrigation check
              <ArrowRight className="size-3.5" />
            </Link>
          </div>
        </Card>
      ) : (
        <Alert tone="info" title="Live weather is not configured" icon={Cloud}>
          {String(weather.detail ?? '')}
        </Alert>
      )}

      {/* Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Irrigation checks"
          value={data.totals.irrigation}
          icon={Droplets}
          tone="blue"
          hint={irrigation ? relativeTime(irrigation.created_at) : 'None yet'}
        />
        <StatCard
          label="Plant analyses"
          value={data.totals.plant}
          icon={Leaf}
          tone="green"
          hint={plant ? relativeTime(plant.created_at) : 'None yet'}
        />
        <StatCard
          label="Soil analyses"
          value={data.totals.soil}
          icon={Mountain}
          tone="amber"
          hint={soil ? relativeTime(soil.created_at) : 'None yet'}
        />
        <StatCard
          label="Plant health trend"
          value={label(trendDirection)}
          icon={TrendIcon}
          tone={trendDirection === 'improving' ? 'green' : trendDirection === 'deteriorating' ? 'red' : 'default'}
        />
      </div>

      {/* Quick actions */}
      <Card>
        <CardHeader title="Quick actions" subtitle="Jump straight into a module" icon={ArrowRight} />
        <div className="grid grid-cols-2 gap-3 p-5 sm:grid-cols-3 lg:grid-cols-6">
          {QUICK_ACTIONS.map((action) => {
            const Icon = action.icon
            return (
              <Link
                key={action.to}
                to={action.to}
                className="group flex flex-col items-center gap-2.5 rounded-xl border border-slate-200 p-4 text-center transition hover:-translate-y-0.5 hover:border-cane-300 hover:shadow-md dark:border-slate-800 dark:hover:border-cane-800"
              >
                <span
                  className={`grid size-11 place-items-center rounded-xl text-white shadow-sm transition group-hover:scale-105 ${action.tone}`}
                >
                  <Icon className="size-5" />
                </span>
                <span className="text-xs font-semibold">{action.label}</span>
              </Link>
            )
          })}
        </div>
      </Card>

      {/* Latest results */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Irrigation */}
        <Card className="flex flex-col">
          <CardHeader title="Latest irrigation" icon={Droplets} />
          <div className="flex-1 p-5">
            {irrigation ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <p className="font-display text-lg font-extrabold">
                    {irrigation.irrigation_required ? 'Irrigate' : 'No irrigation'}
                  </p>
                  <span
                    className={`rounded-full border px-2.5 py-0.5 text-xs font-bold uppercase ${
                      PRIORITY_TONE[irrigation.priority]
                    }`}
                  >
                    {irrigation.priority}
                  </span>
                </div>
                {irrigation.irrigation_required && (
                  <div className="flex gap-4 text-sm">
                    <span>
                      <strong className="font-display text-lg text-sky-600">
                        {formatNumber(irrigation.water_requirement_mm)}
                      </strong>{' '}
                      mm
                    </span>
                    <span>
                      <strong className="font-display text-lg text-cane-600">
                        {irrigation.duration_minutes}
                      </strong>{' '}
                      min
                    </span>
                  </div>
                )}
                <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
                  {irrigation.reason}
                </p>
                <div className="flex items-center justify-between border-t border-slate-100 pt-3 dark:border-slate-800">
                  <span className="text-xs text-slate-400">{formatDate(irrigation.created_at)}</span>
                  <ModelBadge source={irrigation.model_source} />
                </div>
              </div>
            ) : (
              <p className="py-8 text-center text-sm text-slate-500">
                No irrigation check yet.
              </p>
            )}
          </div>
          <div className="border-t border-slate-100 p-4 dark:border-slate-800">
            <Link to="/irrigation" className="btn-ghost w-full text-xs">
              Run a check
              <ArrowRight className="size-3.5" />
            </Link>
          </div>
        </Card>

        {/* Plant */}
        <Card className="flex flex-col">
          <CardHeader title="Latest plant analysis" icon={Leaf} />
          <div className="flex-1 p-5">
            {plant ? (
              <div className="space-y-3">
                {plant.image_url && (
                  <img
                    src={mediaUrl(plant.image_url)}
                    alt={plant.condition_label}
                    className="h-28 w-full rounded-xl object-cover"
                  />
                )}
                <div>
                  <p className="font-display text-base font-extrabold">{plant.condition_label}</p>
                  <p className="text-xs text-slate-500">
                    {percent(plant.confidence)} confidence
                    {plant.severity !== 'none' && ` | ${plant.severity} severity`}
                  </p>
                </div>
                <div className="flex items-center justify-between border-t border-slate-100 pt-3 dark:border-slate-800">
                  <span className="text-xs text-slate-400">{formatDate(plant.created_at)}</span>
                  <ModelBadge source={plant.is_demo ? 'demo_heuristic' : 'trained_model'} />
                </div>
              </div>
            ) : (
              <p className="py-8 text-center text-sm text-slate-500">No plant photo analysed yet.</p>
            )}
          </div>
          <div className="border-t border-slate-100 p-4 dark:border-slate-800">
            <Link to="/plant-analysis" className="btn-ghost w-full text-xs">
              Analyse a photo
              <ArrowRight className="size-3.5" />
            </Link>
          </div>
        </Card>

        {/* Soil */}
        <Card className="flex flex-col">
          <CardHeader title="Latest soil analysis" icon={Mountain} />
          <div className="flex-1 p-5">
            {soil ? (
              <div className="space-y-3">
                {soil.image_url && (
                  <img
                    src={mediaUrl(soil.image_url)}
                    alt={soil.soil_label}
                    className="h-28 w-full rounded-xl object-cover"
                  />
                )}
                <div>
                  <p className="font-display text-base font-extrabold">{soil.soil_label}</p>
                  <p className="text-xs text-slate-500">
                    {percent(soil.confidence)} image confidence | {soil.moisture_appearance} appearance
                  </p>
                </div>
                <p className="border-t border-slate-100 pt-3 text-xs text-slate-400 dark:border-slate-800">
                  {formatDate(soil.created_at)}
                </p>
              </div>
            ) : (
              <p className="py-8 text-center text-sm text-slate-500">No soil photo analysed yet.</p>
            )}
          </div>
          <div className="border-t border-slate-100 p-4 dark:border-slate-800">
            <Link to="/soil-analysis" className="btn-ghost w-full text-xs">
              Analyse soil
              <ArrowRight className="size-3.5" />
            </Link>
          </div>
        </Card>
      </div>

      {/* Chart + tips */}
      <div className="grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader
            title="Soil moisture and water applied"
            subtitle="Your recent irrigation checks"
            icon={Droplets}
          />
          <div className="h-72 p-5">
            {data.irrigation_chart.length > 1 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.irrigation_chart}>
                  <defs>
                    <linearGradient id="moistureFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.35} />
                      <stop offset="100%" stopColor="#0ea5e9" stopOpacity={0.02} />
                    </linearGradient>
                    <linearGradient id="waterFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#16a34a" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#16a34a" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-slate-200 dark:text-slate-800" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip contentStyle={{ borderRadius: 12, fontSize: 12 }} />
                  <Area
                    type="monotone"
                    dataKey="soil_moisture"
                    name="Soil moisture (%)"
                    stroke="#0ea5e9"
                    strokeWidth={2}
                    fill="url(#moistureFill)"
                  />
                  <Area
                    type="monotone"
                    dataKey="water_mm"
                    name="Water needed (mm)"
                    stroke="#16a34a"
                    strokeWidth={2}
                    fill="url(#waterFill)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="grid h-full place-items-center text-center">
                <div>
                  <Droplets className="mx-auto size-10 text-slate-300 dark:text-slate-700" />
                  <p className="mt-3 text-sm text-slate-500">
                    Run at least two irrigation checks to see the trend.
                  </p>
                </div>
              </div>
            )}
          </div>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader title="What to do next" icon={Lightbulb} />
            <ul className="space-y-3 p-5">
              {data.quick_tips.map((tip, index) => (
                <li key={index} className="flex gap-2.5 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                  <span className="mt-[7px] size-1.5 shrink-0 rounded-full bg-cane-500" />
                  {tip}
                </li>
              ))}
            </ul>
          </Card>

          <Card>
            <CardHeader title="AI model status" subtitle="What is actually running" icon={Activity} />
            <div className="space-y-2.5 p-5 text-sm">
              {[
                { key: 'irrigation', name: 'Irrigation', trained: 'irrigation_trained' },
                { key: 'disease', name: 'Disease detection', trained: 'disease_trained' },
                { key: 'soil', name: 'Soil analysis', trained: 'soil_trained' },
              ].map((row) => (
                <div key={row.key} className="flex items-center justify-between gap-2">
                  <span className="text-slate-600 dark:text-slate-400">{row.name}</span>
                  <ModelBadge source={data.model_status[row.key] as ModelSource} />
                </div>
              ))}
              <p className="border-t border-slate-100 pt-3 text-xs leading-relaxed text-slate-500 dark:border-slate-800 dark:text-slate-400">
                Modules marked DEMO use a transparent colour and texture heuristic, not a trained
                neural network. Train a model to switch them over.
              </p>
            </div>
          </Card>
        </div>
      </div>

      {/* Recent history link */}
      {data.totals.total > 0 && (
        <Card>
          <CardHeader
            title="Recent activity"
            subtitle={`${data.totals.total} saved records`}
            icon={History}
            action={
              <Link to="/history" className="btn-secondary shrink-0 px-3 py-1.5 text-xs">
                View all
                <ArrowRight className="size-3.5" />
              </Link>
            }
          />
          <div className="grid gap-3 p-5 sm:grid-cols-3">
            <div className="rounded-xl bg-sky-50 p-4 dark:bg-sky-950/40">
              <p className="font-display text-2xl font-extrabold text-sky-700 dark:text-sky-300">
                {data.totals.irrigation}
              </p>
              <p className="text-xs text-sky-800/80 dark:text-sky-400/80">irrigation checks</p>
            </div>
            <div className="rounded-xl bg-cane-50 p-4 dark:bg-cane-950/40">
              <p className="font-display text-2xl font-extrabold text-cane-700 dark:text-cane-300">
                {data.totals.plant}
              </p>
              <p className="text-xs text-cane-800/80 dark:text-cane-400/80">plant analyses</p>
            </div>
            <div className="rounded-xl bg-soil-50 p-4 dark:bg-soil-950/40">
              <p className="font-display text-2xl font-extrabold text-soil-700 dark:text-soil-300">
                {data.totals.soil}
              </p>
              <p className="text-xs text-soil-800/80 dark:text-soil-400/80">soil analyses</p>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}
