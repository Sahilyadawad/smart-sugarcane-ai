import { useEffect, useState } from 'react'
import {
  Camera,
  Droplets,
  FlaskConical,
  Info,
  Layers,
  Mountain,
  Search,
  Sprout,
  TriangleAlert,
} from 'lucide-react'
import {
  Alert,
  BulletList,
  Card,
  CardHeader,
  Disclaimer,
  EmptyState,
  Field,
  ProgressBar,
  Spinner,
} from '../components/ui'
import { ImageDropzone } from '../components/ImageDropzone'
import { CheckingNotice, UploadHint, ValidationNotice } from '../components/ImageGate'
import { ModelBadge } from '../components/ModelBadge'
import { HonestyNotice } from '../components/HonestyNotice'
import { VarietyCard } from './Varieties'
import { FertilizerPanel } from './Fertilizer'
import { useToast } from '../context/ToastContext'
import { describeError, extractValidation, mediaUrl } from '../services/api'
import { soilApi } from '../services/endpoints'
import { label, percent } from '../utils/format'
import type {
  ClimateType,
  ImageModelStatus,
  ImageValidation,
  PlantingSeason,
  SoilAnalysisResult,
  SoilType,
  WaterAvailability,
} from '../types'

const CLIMATES: ClimateType[] = ['unknown', 'tropical', 'subtropical', 'semi_arid']
const WATER: WaterAvailability[] = ['low', 'medium', 'high']
const SEASONS: PlantingSeason[] = ['general', 'adsali', 'pre_seasonal', 'suru', 'spring', 'autumn']
const SOILS: SoilType[] = ['alluvial', 'black', 'red', 'sandy', 'clay', 'loamy']

export default function SoilAnalysis() {
  const toast = useToast()
  const [file, setFile] = useState<File | null>(null)
  const [context, setContext] = useState({
    region: '',
    district: '',
    climate: 'unknown' as ClimateType,
    irrigation_available: true,
    water_availability: 'medium' as WaterAvailability,
    planting_season: 'general' as PlantingSeason,
    soil_type_override: '' as SoilType | '',
  })
  const [result, setResult] = useState<SoilAnalysisResult | null>(null)
  const [modelStatus, setModelStatus] = useState<ImageModelStatus | null>(null)
  const [analysing, setAnalysing] = useState(false)
  const [validating, setValidating] = useState(false)
  const [validation, setValidation] = useState<ImageValidation | null>(null)

  useEffect(() => {
    soilApi.modelStatus().then(setModelStatus).catch(() => setModelStatus(null))
  }, [])

  /**
   * Check the photo the moment it is chosen, before any analysis is offered.
   *
   * The backend runs this same gate inside /soil/analyze, so this is for a
   * clear, immediate message - it is not what enforces the restriction.
   */
  const runValidation = async (chosen: File): Promise<ImageValidation | null> => {
    setValidating(true)
    try {
      const check = await soilApi.validateImage(chosen)
      setValidation(check)
      return check
    } catch (caught) {
      toast.error('Could not check the photo', describeError(caught))
      setValidation(null)
      return null
    } finally {
      setValidating(false)
    }
  }

  const handleSelect = (chosen: File | null) => {
    setFile(chosen)
    setValidation(null)
    setResult(null)
    if (chosen) void runValidation(chosen)
  }

  const handleAnalyse = async () => {
    if (!file) {
      toast.info('Choose a photo first', 'Upload a picture of bare, freshly turned soil.')
      return
    }
    // The gate already ran when the file was chosen. Re-run only if that check
    // never completed, so a transient failure cannot leave the button unusable.
    let check = validation
    if (!check) {
      check = await runValidation(file)
      if (!check) return
    }
    if (!check.isSugarcane) {
      toast.info('Soil not detected', check.title)
      return
    }

    setAnalysing(true)
    try {
      const data = await soilApi.analyze(file, {
        region: context.region || undefined,
        district: context.district || undefined,
        climate: context.climate,
        irrigation_available: context.irrigation_available,
        water_availability: context.water_availability,
        planting_season: context.planting_season,
        soil_type_override: context.soil_type_override || undefined,
      })
      setResult(data)
      toast.success(
        `Visual estimate: ${data.estimate.soil_label}`,
        `${percent(data.estimate.confidence)} image confidence - laboratory testing gives accurate nutrient values`,
      )
      requestAnimationFrame(() =>
        document.getElementById('soil-result')?.scrollIntoView({ behavior: 'smooth', block: 'start' }),
      )
    } catch (caught) {
      const rejected = extractValidation(caught)
      if (rejected) {
        setValidation(rejected)
        setResult(null)
        toast.info('Soil not detected', rejected.message)
      } else {
        toast.error('Analysis failed', describeError(caught))
      }
    } finally {
      setAnalysing(false)
    }
  }

  const estimate = result?.estimate

  return (
    <div className="space-y-6">
      <div>
        <h2 className="font-display text-2xl font-extrabold">Soil Analysis</h2>
        <p className="mt-1 text-slate-600 dark:text-slate-400">
          A visual estimate from a photo of bare soil, followed by variety and fertilizer guidance.
        </p>
      </div>

      {modelStatus && (
        <HonestyNotice
          source={modelStatus.trained_model_available ? 'trained_model' : 'demo_heuristic'}
          summary={
            modelStatus.trained_model_available
              ? 'Trained soil model in use. A photo still cannot measure NPK or pH.'
              : 'Visual estimate from colour and texture. A photo cannot measure NPK or pH.'
          }
          notes={modelStatus.notes}
        >
          <p>
            This is a <strong>visual estimate</strong>. A photograph cannot determine exact NPK
            values, pH, electrical conductivity or micronutrient concentrations. Laboratory soil
            testing provides accurate nutrient and pH values - use this to decide whether a test is
            worth ordering, not instead of one.
          </p>
        </HonestyNotice>
      )}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,420px)_1fr]">
        <Card className="h-fit">
          <CardHeader title="Upload a soil photo" subtitle="Bare, freshly turned soil" icon={Camera} />
          <div className="space-y-5 p-5">
            <UploadHint kind="soil" />

            <ImageDropzone
              onSelect={handleSelect}
              disabled={analysing || validating}
              label="Upload a soil photo"
              hint="Photograph a levelled patch of bare soil from about 30-40 cm in indirect daylight. Keep grass, hands and tools out of the frame."
            />

            <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-800">
              <h4 className="mb-3 text-sm font-bold">Farm details (optional)</h4>
              <p className="mb-4 text-xs text-slate-500 dark:text-slate-400">
                These sharpen the variety recommendations. Leave blank if you are not sure.
              </p>

              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <Field label="State / region" htmlFor="region">
                    <input
                      id="region"
                      className="input"
                      placeholder="Karnataka"
                      value={context.region}
                      onChange={(event) => setContext((c) => ({ ...c, region: event.target.value }))}
                    />
                  </Field>
                  <Field label="District" htmlFor="district">
                    <input
                      id="district"
                      className="input"
                      placeholder="Belagavi"
                      value={context.district}
                      onChange={(event) => setContext((c) => ({ ...c, district: event.target.value }))}
                    />
                  </Field>
                </div>

                <Field label="Climate type" htmlFor="climate">
                  <select
                    id="climate"
                    className="input"
                    value={context.climate}
                    onChange={(event) =>
                      setContext((c) => ({ ...c, climate: event.target.value as ClimateType }))
                    }
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
                    value={context.water_availability}
                    onChange={(event) =>
                      setContext((c) => ({
                        ...c,
                        water_availability: event.target.value as WaterAvailability,
                      }))
                    }
                  >
                    {WATER.map((option) => (
                      <option key={option} value={option}>
                        {label(option)}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field label="Preferred planting season" htmlFor="season">
                  <select
                    id="season"
                    className="input"
                    value={context.planting_season}
                    onChange={(event) =>
                      setContext((c) => ({ ...c, planting_season: event.target.value as PlantingSeason }))
                    }
                  >
                    {SEASONS.map((option) => (
                      <option key={option} value={option}>
                        {label(option)}
                      </option>
                    ))}
                  </select>
                </Field>

                <Field
                  label="Known soil type"
                  htmlFor="override"
                  hint="If a laboratory test already told you the soil type, this overrides the photo estimate."
                >
                  <select
                    id="override"
                    className="input"
                    value={context.soil_type_override}
                    onChange={(event) =>
                      setContext((c) => ({ ...c, soil_type_override: event.target.value as SoilType | '' }))
                    }
                  >
                    <option value="">Use the photo estimate</option>
                    {SOILS.map((option) => (
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
                    checked={context.irrigation_available}
                    onChange={(event) =>
                      setContext((c) => ({ ...c, irrigation_available: event.target.checked }))
                    }
                  />
                  Assured irrigation is available
                </label>
              </div>
            </div>

            <button
              type="button"
              onClick={handleAnalyse}
              disabled={analysing || validating || !file || validation?.isSugarcane === false}
              className="btn-primary w-full"
            >
              {analysing || validating ? <Spinner className="size-4" /> : <Search className="size-4" />}
              {validating ? 'Checking this is soil...' : analysing ? 'Analysing soil...' : 'Analyze Soil'}
            </button>

            {validating && <CheckingNotice kind="soil" />}
            {!validating && validation && (
              <ValidationNotice
                validation={validation}
                onRetry={validation.isSugarcane ? undefined : () => {
                  setFile(null)
                  setValidation(null)
                }}
              />
            )}

            {analysing && (
              <div className="space-y-2 rounded-xl bg-slate-50 p-4 dark:bg-slate-800/50">
                <p className="text-xs font-medium text-slate-600 dark:text-slate-400">
                  Measuring colour, saturation and grain texture...
                </p>
                <ProgressBar value={65} tone="amber" />
              </div>
            )}
          </div>
        </Card>

        <div className="space-y-6" id="soil-result">
          {!estimate || !result ? (
            <Card className="min-h-[420px]">
              <EmptyState
                icon={Mountain}
                title="No soil analysis yet"
                description="Upload a soil photo and press Analyze Soil. You will get a visual soil category, moisture and texture appearance, then variety and fertilizer guidance based on it."
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
                        alt="Analysed soil sample"
                        className="h-full max-h-64 w-full object-cover md:max-h-none"
                      />
                    </div>
                  )}
                  <div className="p-6">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          Possible soil category
                        </p>
                        <h3 className="mt-1 font-display text-2xl font-extrabold">
                          {estimate.soil_label}
                        </h3>
                      </div>
                      <div className="flex items-center gap-2">
                        <span
                          className="size-9 rounded-lg border border-slate-300 shadow-inner dark:border-slate-600"
                          style={{
                            backgroundColor: `rgb(${estimate.dominant_rgb.join(',')})`,
                          }}
                          title={`Dominant colour: rgb(${estimate.dominant_rgb.join(', ')})`}
                        />
                        <ModelBadge source={result.model_source} />
                      </div>
                    </div>

                    <div className="mt-4">
                      <div className="mb-1.5 flex justify-between text-xs font-medium">
                        <span className="text-slate-500">Image confidence</span>
                        <span>{percent(estimate.confidence, 1)}</span>
                      </div>
                      <ProgressBar
                        value={estimate.confidence * 100}
                        tone={estimate.confidence > 0.65 ? 'green' : estimate.confidence > 0.42 ? 'amber' : 'red'}
                      />
                    </div>

                    <dl className="mt-5 grid gap-3 sm:grid-cols-2">
                      {[
                        { term: 'Possible colour', value: estimate.colour_description },
                        { term: 'Texture appearance', value: estimate.texture_appearance },
                        { term: 'Moisture appearance', value: estimate.moisture_label },
                        { term: 'Organic matter', value: estimate.organic_matter_label },
                      ].map((item) => (
                        <div key={item.term} className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/60">
                          <dt className="text-xs font-medium text-slate-500">{item.term}</dt>
                          <dd className="mt-0.5 text-sm font-semibold">{item.value}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                </div>
              </Card>

              <Disclaimer>{result.lab_test_notice}</Disclaimer>

              <div className="grid gap-6 lg:grid-cols-2">
                <Card>
                  <CardHeader title="What this soil usually means" icon={Layers} />
                  <div className="space-y-4 p-5">
                    <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                      {estimate.visual_description}
                    </p>
                    <BulletList items={estimate.general_properties} />
                    <div className="rounded-lg bg-cane-50 p-3 text-sm dark:bg-cane-950/40">
                      <p className="font-semibold text-cane-900 dark:text-cane-200">
                        Sugarcane suitability
                      </p>
                      <p className="mt-1 text-cane-800/90 dark:text-cane-300/90">
                        {estimate.sugarcane_suitability}
                      </p>
                    </div>
                    <div className="flex gap-2.5 rounded-lg bg-sky-50 p-3 text-sm dark:bg-sky-950/40">
                      <Droplets className="mt-0.5 size-4 shrink-0 text-sky-600" />
                      <p className="text-sky-900 dark:text-sky-200">{estimate.irrigation_note}</p>
                    </div>
                  </div>
                </Card>

                <Card>
                  <CardHeader title="Management notes" icon={Sprout} />
                  <div className="space-y-4 p-5">
                    <BulletList items={estimate.management_notes} tone="success" />
                    <div className="border-t border-slate-100 pt-4 dark:border-slate-800">
                      <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">
                        Moisture note
                      </p>
                      <p className="text-sm text-slate-600 dark:text-slate-400">{estimate.moisture_note}</p>
                    </div>
                    <div className="border-t border-slate-100 pt-4 dark:border-slate-800">
                      <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">
                        Organic matter note
                      </p>
                      <p className="text-sm text-slate-600 dark:text-slate-400">
                        {estimate.organic_matter_note}
                      </p>
                    </div>
                  </div>
                </Card>
              </div>

              {/* Class distribution */}
              <Card>
                <CardHeader title="All soil categories considered" icon={Mountain} />
                <div className="space-y-3 p-5">
                  {estimate.probabilities.slice(0, 6).map((entry) => (
                    <div key={entry.key}>
                      <div className="mb-1 flex justify-between text-xs">
                        <span
                          className={
                            entry.key === estimate.soil_type
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
                        tone={entry.key === estimate.soil_type ? 'green' : 'blue'}
                      />
                    </div>
                  ))}
                </div>
              </Card>

              {/* Varieties */}
              {result.varieties && (
                <Card>
                  <CardHeader
                    title="Recommended sugarcane varieties"
                    subtitle={`Ranked against ${result.varieties.criteria_used.join(' | ')}`}
                    icon={Sprout}
                  />
                  <div className="space-y-4 p-5">
                    <div className="grid gap-4 lg:grid-cols-2">
                      {result.varieties.matches.map((match) => (
                        <VarietyCard key={match.id} match={match} />
                      ))}
                    </div>
                    <Alert tone="info" icon={Info}>
                      {result.varieties.disclaimer}
                    </Alert>
                  </div>
                </Card>
              )}

              {/* Fertilizer */}
              {result.fertilizer && (
                <Card>
                  <CardHeader
                    title="Fertilizer guidance"
                    subtitle="Based on this soil estimate, at the tillering stage"
                    icon={FlaskConical}
                  />
                  <div className="p-5">
                    <FertilizerPanel data={result.fertilizer} />
                  </div>
                </Card>
              )}

              {/* Limitations */}
              <Card className="border-amber-200 dark:border-amber-900">
                <CardHeader
                  title="Limitations of image-based soil analysis"
                  subtitle="Read this before acting on the estimate"
                  icon={TriangleAlert}
                />
                <div className="grid gap-6 p-5 lg:grid-cols-2">
                  <div>
                    <h4 className="mb-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                      What a photo cannot determine
                    </h4>
                    <BulletList items={result.limitations} tone="warning" />
                  </div>
                  <div>
                    <h4 className="mb-3 text-xs font-bold uppercase tracking-wide text-slate-500">
                      How to take a better photo
                    </h4>
                    <BulletList items={result.improve_photo_tips} />
                  </div>
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
    </div>
  )
}
