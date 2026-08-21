import { useCallback, useEffect, useState } from 'react'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Activity,
  AlertTriangle,
  CalendarClock,
  Camera,
  Droplets,
  HeartPulse,
  Leaf,
  Search,
  Shield,
  Sprout,
  Stethoscope,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'
import {
  Alert,
  BulletList,
  Card,
  CardHeader,
  Disclaimer,
  EmptyState,
  Field,
  NumberedList,
  ProgressBar,
  Spinner,
  StatCard,
} from '../components/ui'
import { ImageDropzone } from '../components/ImageDropzone'
import { ModelBadge } from '../components/ModelBadge'
import { HonestyNotice } from '../components/HonestyNotice'
import { useToast } from '../context/ToastContext'
import { describeError, mediaUrl } from '../services/api'
import { plantApi } from '../services/endpoints'
import { SEVERITY_TONE, formatDate, label, percent } from '../utils/format'
import type { GrowthStage, ImageModelStatus, PlantAnalysisResult, PlantTrend } from '../types'

const GROWTH_STAGES: GrowthStage[] = [
  'germination',
  'tillering',
  'grand_growth',
  'maturation',
  'ratoon_initiation',
]

const TREND_ICON = {
  improving: TrendingUp,
  deteriorating: TrendingDown,
  stable: Activity,
  insufficient_data: Activity,
}

export default function PlantAnalysis() {
  const toast = useToast()
  const [file, setFile] = useState<File | null>(null)
  const [growthStage, setGrowthStage] = useState<GrowthStage | ''>('')
  const [notes, setNotes] = useState('')
  const [result, setResult] = useState<PlantAnalysisResult | null>(null)
  const [trend, setTrend] = useState<PlantTrend | null>(null)
  const [modelStatus, setModelStatus] = useState<ImageModelStatus | null>(null)
  const [analysing, setAnalysing] = useState(false)

  const loadTrend = useCallback(async () => {
    try {
      setTrend(await plantApi.trend(12))
    } catch {
      // Trend is supplementary; a failure here should not block analysis.
    }
  }, [])

  useEffect(() => {
    void loadTrend()
    plantApi.modelStatus().then(setModelStatus).catch(() => setModelStatus(null))
  }, [loadTrend])

  const handleAnalyse = async () => {
    if (!file) {
      toast.info('Choose a photo first', 'Upload a picture of a sugarcane leaf, stem or plant.')
      return
    }
    setAnalysing(true)
    try {
      const data = await plantApi.analyze(file, growthStage || undefined, notes || undefined)
      setResult(data)
      toast.success(
        `Detected: ${data.condition_label}`,
        `${percent(data.confidence)} confidence${data.is_demo ? ' - DEMO mode' : ''}`,
      )
      void loadTrend()
      requestAnimationFrame(() =>
        document.getElementById('plant-result')?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
      )
    } catch (caught) {
      toast.error('Analysis failed', describeError(caught))
    } finally {
      setAnalysing(false)
    }
  }

  const TrendIcon = TREND_ICON[trend?.direction ?? 'insufficient_data']

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-2xl font-extrabold">Plant Health Analysis</h2>
        <p className="mt-1 text-slate-600 dark:text-slate-400">
          Upload a photo of a sugarcane leaf, stem or plant for a condition estimate and a recovery plan.
        </p>
      </div>

      {modelStatus && (
        <HonestyNotice
          source={modelStatus.trained_model_available ? 'trained_model' : 'demo_heuristic'}
          summary={
            modelStatus.trained_model_available
              ? 'Trained image classifier in use. Confirm findings with an agricultural officer.'
              : 'Colour and texture estimate, not a trained network. Illustrative only.'
          }
          notes={modelStatus.notes}
        >
          <p>
            No labelled sugarcane disease dataset ships with this project, so the analyser runs a
            transparent colour and texture heuristic instead of a trained neural network. It responds
            to what is actually in your photo, but it is <strong>not a diagnosis</strong>. See
            docs/DATASET_GUIDE.md to train a real model.
          </p>
        </HonestyNotice>
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,420px)_1fr]">
        {/* Upload */}
        <Card className="h-fit">
          <CardHeader title="Upload a photo" subtitle="Leaf, stem or whole plant" icon={Camera} />
          <div className="space-y-5 p-5">
            <ImageDropzone
              onSelect={setFile}
              disabled={analysing}
              label="Upload a sugarcane photo"
              hint="Fill the frame with the affected leaf or stalk, in daylight, avoiding deep shade and direct flash."
            />

            <Field
              label="Growth stage (optional)"
              htmlFor="stage"
              hint="Tailors the recovery plan to where the crop is in the season."
            >
              <select
                id="stage"
                className="input"
                value={growthStage}
                onChange={(event) => setGrowthStage(event.target.value as GrowthStage | '')}
              >
                <option value="">Not sure</option>
                {GROWTH_STAGES.map((stage) => (
                  <option key={stage} value={stage}>
                    {label(stage)}
                  </option>
                ))}
              </select>
            </Field>

            <Field label="Notes (optional)" htmlFor="notes">
              <textarea
                id="notes"
                rows={3}
                className="input resize-none"
                placeholder="Which block, when you first noticed it, how many plants are affected..."
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
              />
            </Field>

            <button
              type="button"
              onClick={handleAnalyse}
              disabled={analysing || !file}
              className="btn-primary w-full"
            >
              {analysing ? <Spinner className="size-4" /> : <Search className="size-4" />}
              {analysing ? 'Analysing image...' : 'Analyze Plant'}
            </button>

            {analysing && (
              <div className="space-y-2 rounded-xl bg-slate-50 p-4 dark:bg-slate-800/50">
                <p className="text-xs font-medium text-slate-600 dark:text-slate-400">
                  Reading colour, texture and lesion structure...
                </p>
                <ProgressBar value={70} tone="green" />
              </div>
            )}
          </div>
        </Card>

        {/* Result */}
        <div className="space-y-6" id="plant-result">
          {!result ? (
            <Card className="min-h-[420px]">
              <EmptyState
                icon={Leaf}
                title="No analysis yet"
                description="Upload a photo and press Analyze Plant. You will get the likely condition, a confidence score, a severity rating and a step-by-step recovery plan."
              />
            </Card>
          ) : (
            <>
              <Card className="overflow-hidden">
                <div className="grid gap-0 md:grid-cols-[220px_1fr]">
                  {result.image_url && (
                    <div className="bg-slate-100 dark:bg-slate-800">
                      <img
                        src={mediaUrl(result.image_url)}
                        alt="Analysed sugarcane plant"
                        className="h-full max-h-64 w-full object-cover md:max-h-none"
                      />
                    </div>
                  )}
                  <div className="p-6">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Detected condition
                        </p>
                        <h3 className="mt-1 font-display text-2xl font-extrabold">
                          {result.condition_label}
                        </h3>
                        <p className="mt-1 text-xs capitalize text-slate-500">
                          {result.pathogen_type !== 'none' && result.pathogen_type !== 'undetermined'
                            ? `${result.pathogen_type} disease`
                            : label(result.pathogen_type)}
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        <span
                          className={`rounded-full border px-3 py-1 text-xs font-bold uppercase ${
                            SEVERITY_TONE[result.severity]
                          }`}
                        >
                          {result.severity === 'none' ? 'Healthy' : `${result.severity} severity`}
                        </span>
                        <ModelBadge source={result.model_source} />
                      </div>
                    </div>

                    <div className="mt-5 grid gap-4 sm:grid-cols-2">
                      <div>
                        <div className="mb-1.5 flex justify-between text-xs font-medium">
                          <span className="text-slate-500">Confidence</span>
                          <span>{percent(result.confidence, 1)}</span>
                        </div>
                        <ProgressBar
                          value={result.confidence * 100}
                          tone={result.confidence > 0.7 ? 'green' : result.confidence > 0.45 ? 'amber' : 'red'}
                        />
                      </div>
                      <div>
                        <div className="mb-1.5 flex justify-between text-xs font-medium">
                          <span className="text-slate-500">Plant health score</span>
                          <span>{result.health_score.toFixed(0)} / 100</span>
                        </div>
                        <ProgressBar
                          value={result.health_score}
                          tone={result.health_score > 70 ? 'green' : result.health_score > 40 ? 'amber' : 'red'}
                        />
                      </div>
                    </div>

                    <p className="mt-4 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                      {result.short_description}
                    </p>
                    <p className="mt-2 text-sm font-medium text-slate-700 dark:text-slate-300">
                      {result.severity_note}
                    </p>
                  </div>
                </div>
              </Card>

              <Disclaimer>{result.disclaimer}</Disclaimer>

              {result.image_quality.issues.length > 0 && (
                <Alert tone="warning" title={`Image quality: ${result.image_quality.rating}`}>
                  <ul className="list-disc space-y-1 pl-4">
                    {result.image_quality.issues.map((issue, index) => (
                      <li key={index}>{issue}</li>
                    ))}
                  </ul>
                </Alert>
              )}

              {/* Probabilities */}
              <Card>
                <CardHeader
                  title="All considered conditions"
                  subtitle="The full distribution, not just the top answer"
                  icon={Stethoscope}
                />
                <div className="space-y-3 p-5">
                  {result.probabilities.slice(0, 7).map((entry) => (
                    <div key={entry.key}>
                      <div className="mb-1 flex justify-between text-xs">
                        <span
                          className={
                            entry.key === result.detected_condition
                              ? 'font-bold text-slate-800 dark:text-slate-200'
                              : 'text-slate-500'
                          }
                        >
                          {entry.label}
                        </span>
                        <span className="tabular-nums text-slate-500">{percent(entry.probability, 1)}</span>
                      </div>
                      <ProgressBar
                        value={entry.probability * 100}
                        tone={entry.key === result.detected_condition ? 'green' : 'blue'}
                      />
                    </div>
                  ))}
                </div>
              </Card>

              {/* Symptoms and causes */}
              <div className="grid gap-6 lg:grid-cols-2">
                <Card>
                  <CardHeader title="Possible symptoms" icon={AlertTriangle} />
                  <div className="p-5">
                    <BulletList items={result.symptoms} tone="warning" />
                  </div>
                </Card>
                <Card>
                  <CardHeader title="Possible causes" icon={Search} />
                  <div className="p-5">
                    <BulletList items={result.causes} />
                  </div>
                </Card>
              </div>

              {/* Recovery */}
              <Card className="border-cane-200 dark:border-cane-900">
                <div className="border-b border-cane-100 bg-cane-50 p-5 dark:border-cane-900 dark:bg-cane-950/40">
                  <h3 className="flex items-center gap-2 font-display text-lg font-extrabold text-cane-900 dark:text-cane-200">
                    <Sprout className="size-5" />
                    How to improve this plant
                  </h3>
                  <p className="mt-1 text-sm text-cane-800/80 dark:text-cane-300/80">
                    Tailored to the detected condition, its severity
                    {result.growth_stage ? ` and the ${label(result.growth_stage)} stage` : ''}.
                  </p>
                </div>

                <div className="grid gap-6 p-5 lg:grid-cols-2">
                  <section>
                    <h4 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-slate-500">
                      <AlertTriangle className="size-4" />
                      Immediate action
                    </h4>
                    <NumberedList items={result.recovery.immediate_action} />
                  </section>

                  <section>
                    <h4 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-slate-500">
                      <HeartPulse className="size-4" />
                      Plant recovery plan
                    </h4>
                    <BulletList items={result.recovery.recovery_plan} tone="success" />
                  </section>

                  <section>
                    <h4 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-slate-500">
                      <Droplets className="size-4" />
                      Irrigation advice
                    </h4>
                    {result.recovery.irrigation_advice.summary && (
                      <p className="mb-3 rounded-lg bg-sky-50 p-3 text-sm font-medium text-sky-900 dark:bg-sky-950/50 dark:text-sky-200">
                        {result.recovery.irrigation_advice.summary}
                      </p>
                    )}
                    <BulletList items={result.recovery.irrigation_advice.details ?? []} />
                  </section>

                  <section>
                    <h4 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-slate-500">
                      <Sprout className="size-4" />
                      Soil and nutrient advice
                    </h4>
                    <BulletList items={result.recovery.soil_and_nutrient_advice} />
                  </section>

                  <section>
                    <h4 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-slate-500">
                      <Shield className="size-4" />
                      Prevention plan
                    </h4>
                    <BulletList items={result.recovery.prevention_plan} />
                  </section>

                  <section>
                    <h4 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase tracking-wide text-slate-500">
                      <CalendarClock className="size-4" />
                      Monitoring schedule
                    </h4>
                    <BulletList items={result.recovery.monitoring_schedule} />
                  </section>
                </div>
              </Card>

              {result.model_notes.length > 0 && (
                <Alert tone={result.is_demo ? 'warning' : 'info'} title="Model notes">
                  <ul className="list-disc space-y-1 pl-4">
                    {result.model_notes.map((note, index) => (
                      <li key={index}>{note}</li>
                    ))}
                  </ul>
                </Alert>
              )}
            </>
          )}
        </div>
      </div>

      {/* Plant health history */}
      <Card>
        <CardHeader
          title="Plant health history"
          subtitle="Upload photos over time to see whether the crop is improving"
          icon={TrendIcon}
        />
        {!trend || trend.points.length === 0 ? (
          <EmptyState
            icon={Camera}
            title="No history yet"
            description="Analyse a plant photo to start tracking. Uploading a follow-up photo of the same block after 7 days gives you a comparison."
          />
        ) : (
          <div className="p-5">
            <div className="grid gap-4 sm:grid-cols-3">
              <StatCard
                label="Trend"
                value={label(trend.direction)}
                icon={TrendIcon}
                tone={
                  trend.direction === 'improving'
                    ? 'green'
                    : trend.direction === 'deteriorating'
                      ? 'red'
                      : 'default'
                }
              />
              <StatCard label="Analyses" value={trend.points.length} icon={Camera} tone="blue" />
              <StatCard
                label="Latest health score"
                value={trend.points[trend.points.length - 1].health_score.toFixed(0)}
                unit="/100"
                icon={HeartPulse}
                tone="green"
              />
            </div>

            <p className="mt-4 text-sm text-slate-600 dark:text-slate-400">{trend.summary}</p>
            {trend.comparison_note && (
              <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{trend.comparison_note}</p>
            )}

            {trend.points.length > 1 && (
              <div className="mt-6 h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={trend.points.map((point) => ({
                      date: formatDate(point.date),
                      health: point.health_score,
                      confidence: Math.round(point.confidence * 100),
                      condition: point.condition_label,
                    }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-slate-200 dark:text-slate-800" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{ borderRadius: 12, fontSize: 12 }}
                      formatter={(value: number, name: string) => [value, name === 'health' ? 'Health score' : 'Confidence %']}
                    />
                    <Line type="monotone" dataKey="health" name="Health score" stroke="#16a34a" strokeWidth={2.5} dot={{ r: 4 }} />
                    <Line type="monotone" dataKey="confidence" name="Confidence %" stroke="#94a3b8" strokeWidth={1.5} strokeDasharray="4 4" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[...trend.points].reverse().slice(0, 4).map((point) => (
                <div
                  key={point.id}
                  className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-800"
                >
                  <img
                    src={mediaUrl(point.image_url)}
                    alt={`${point.condition_label} on ${formatDate(point.date)}`}
                    className="h-28 w-full object-cover"
                  />
                  <div className="p-3">
                    <p className="truncate text-xs font-bold">{point.condition_label}</p>
                    <p className="mt-0.5 text-xs text-slate-500">{formatDate(point.date)}</p>
                    <div className="mt-2">
                      <ProgressBar
                        value={point.health_score}
                        tone={point.health_score > 70 ? 'green' : point.health_score > 40 ? 'amber' : 'red'}
                        showLabel
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
