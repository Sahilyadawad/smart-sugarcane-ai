/** Shared API types. These mirror the pydantic schemas in backend/app/schemas. */

export type SoilType = 'alluvial' | 'black' | 'red' | 'sandy' | 'clay' | 'loamy' | 'mixed'
export type GrowthStage =
  | 'germination'
  | 'tillering'
  | 'grand_growth'
  | 'maturation'
  | 'ratoon_initiation'
export type WeatherCondition =
  | 'clear'
  | 'partly_cloudy'
  | 'cloudy'
  | 'rainy'
  | 'stormy'
  | 'humid'
  | 'dry_wind'
export type IrrigationMethod = 'flood' | 'furrow' | 'sprinkler' | 'drip'
export type WaterAvailability = 'low' | 'medium' | 'high'
export type Priority = 'low' | 'medium' | 'high' | 'critical'
export type Severity = 'none' | 'mild' | 'moderate' | 'severe' | 'undetermined'
export type ClimateType = 'tropical' | 'subtropical' | 'semi_arid' | 'unknown'
export type PlantingSeason =
  | 'adsali'
  | 'pre_seasonal'
  | 'suru'
  | 'spring'
  | 'autumn'
  | 'general'

/** Every AI response carries this so the UI can label demo output honestly. */
export type ModelSource = 'trained_model' | 'rule_engine' | 'demo_heuristic'

// ---------------------------------------------------------------- auth
export interface User {
  id: number
  name: string
  email: string
  phone?: string | null
  farm_location?: string | null
  language: string
  theme: string
  notifications_enabled: boolean
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

// ---------------------------------------------------------- irrigation
export interface IrrigationInput {
  soil_moisture: number
  temperature: number
  humidity: number
  rainfall: number
  rain_probability: number
  wind_speed: number
  weather_condition: WeatherCondition
  soil_type: SoilType
  growth_stage: GrowthStage
  irrigation_method: IrrigationMethod
  area_hectares: number
  save?: boolean
}

export interface FeatureContribution {
  feature: string
  label: string
  value: number
  impact: number
  note: string
}

export interface IrrigationResult {
  irrigation_required: boolean
  priority: Priority
  water_requirement_mm: number
  water_volume_liters: number
  water_volume_per_hectare: number
  duration_minutes: number
  recommended_window: string
  next_check_hours: number
  soil_moisture_status: string
  deficit_mm: number
  crop_water_use_mm: number
  effective_rain_mm: number
  reference_et_mm: number
  crop_coefficient: number
  reason: string
  explanation: string[]
  water_saving_tips: string[]
  rain_forecast_note: string
  model_source: ModelSource
  model_label: string
  model_confidence: number
  model_notes: string[]
  feature_contributions: FeatureContribution[]
  disclaimer: string
  record_id?: number | null
  created_at?: string | null
}

export interface IrrigationModelStatus {
  trained_model_available: boolean
  model_path: string | null
  model_source: string
  trained_at?: string | null
  dataset_rows?: number | null
  dataset_type?: string | null
  metrics?: Record<string, number> | null
  notes: string[]
}

export interface IrrigationChartPoint {
  date: string
  timestamp: string
  soil_moisture: number
  temperature: number
  water_mm: number
  priority: Priority
  required: boolean
}

// --------------------------------------------------------------- plant
export interface ClassProbability {
  key: string
  label: string
  probability: number
}

export interface ImageQuality {
  rating: string
  score: number
  issues: string[]
  resolution: string
  sharpness: number
  brightness: number
}

export interface RecoveryPlan {
  immediate_action: string[]
  recovery_plan: string[]
  irrigation_advice: { summary?: string; details?: string[] }
  soil_and_nutrient_advice: string[]
  prevention_plan: string[]
  monitoring_schedule: string[]
}

export interface PlantAnalysisResult {
  id?: number | null
  image_url?: string | null
  detected_condition: string
  condition_label: string
  pathogen_type: string
  confidence: number
  severity: Severity
  severity_note: string
  health_score: number
  short_description: string
  symptoms: string[]
  causes: string[]
  management: string[]
  prevention: string[]
  recovery: RecoveryPlan
  probabilities: ClassProbability[]
  image_quality: ImageQuality
  model_source: ModelSource
  model_label: string
  is_demo: boolean
  model_notes: string[]
  disclaimer: string
  growth_stage?: string | null
  created_at?: string | null
}

export interface PlantTrendPoint {
  id: number
  date: string
  condition: string
  condition_label: string
  severity: Severity
  confidence: number
  health_score: number
  image_url: string
}

export interface PlantTrend {
  points: PlantTrendPoint[]
  direction: 'improving' | 'stable' | 'deteriorating' | 'insufficient_data'
  summary: string
  first_seen?: string | null
  last_seen?: string | null
  comparison_note: string
}

export interface ImageModelStatus {
  trained_model_available: boolean
  model_path: string | null
  model_source: string
  mode: string
  class_names: string[]
  notes: string[]
}

// ---------------------------------------------------------------- soil
export interface SoilVisualEstimate {
  soil_type: SoilType
  soil_label: string
  confidence: number
  colour_description: string
  dominant_rgb: number[]
  texture_appearance: string
  moisture_appearance: string
  moisture_label: string
  moisture_note: string
  organic_matter_appearance: string
  organic_matter_label: string
  organic_matter_note: string
  visual_description: string
  general_properties: string[]
  sugarcane_suitability: string
  management_notes: string[]
  irrigation_note: string
  probabilities: ClassProbability[]
  image_quality: ImageQuality
}

export interface SoilAnalysisResult {
  id?: number | null
  image_url?: string | null
  estimate: SoilVisualEstimate
  limitations: string[]
  improve_photo_tips: string[]
  varieties?: VarietyRecommendation | null
  fertilizer?: FertilizerRecommendation | null
  model_source: ModelSource
  model_label: string
  is_demo: boolean
  model_notes: string[]
  disclaimer: string
  lab_test_notice: string
  created_at?: string | null
}

// ------------------------------------------------------ recommendations
export interface VarietyMatch {
  id: string
  name: string
  aliases: string[]
  released_by: string
  match_score: number
  match_label: string
  why_suitable: string[]
  soil_suitability: string[]
  water_requirement: string
  climate_suitability: string[]
  maturity: string
  duration_months: string
  planting_seasons: string[]
  ratooning: string
  disease_notes: string
  strengths: string[]
  cautions: string[]
  source_note: string
}

export interface VarietyRecommendation {
  matches: VarietyMatch[]
  considered: number
  criteria_used: string[]
  score_explanation: string
  disclaimer: string
  data_disclaimer: string
  last_reviewed: string
}

export interface NutrientFocus {
  nutrient: string
  priority: 'low' | 'medium' | 'high'
  reason: string
  lab_rating?: string | null
}

export interface SplitScheduleEntry {
  stage: string
  label: string
  window: string
  focus: string
  timing_note: string
  nutrient_priority: Record<string, string>
  is_current: boolean
  is_past: boolean
  soil_note?: string
}

export interface FertilizerRecommendation {
  growth_stage: string
  growth_stage_label: string
  typical_window: string
  stage_goal: string
  stage_focus: string
  nutrient_focus: NutrientFocus[]
  suggested_management: string[]
  split_schedule: SplitScheduleEntry[]
  organic_matter_advice: string
  soil_specific_notes: string[]
  ph_note?: string | null
  water_note: string
  plant_health_note: string
  lab_values_used: boolean
  general_practices: string[]
  disclaimer: string
  data_disclaimer: string
}

// ------------------------------------------------------------- history
export interface HistoryItem {
  id: number
  kind: 'plant' | 'soil' | 'irrigation'
  title: string
  subtitle: string
  badge: string
  badge_tone: 'success' | 'warning' | 'danger' | 'info'
  image_url?: string | null
  created_at: string
}

export interface HistoryPage {
  items: HistoryItem[]
  total: number
  page: number
  page_size: number
  counts: { plant: number; soil: number; irrigation: number; total: number }
}

export interface HistoryDetail {
  id: number
  kind: string
  created_at: string
  payload: Record<string, unknown>
}

// ----------------------------------------------------------- dashboard
export interface DashboardSummary {
  user_name: string
  greeting: string
  totals: { plant: number; soil: number; irrigation: number; total: number }
  latest_plant: Record<string, never> | null | Record<string, unknown>
  latest_soil: Record<string, unknown> | null
  latest_irrigation: Record<string, unknown> | null
  weather: Record<string, unknown> | null
  plant_trend: PlantTrend
  irrigation_chart: IrrigationChartPoint[]
  quick_tips: string[]
  model_status: Record<string, string | boolean>
}

// ----------------------------------------------------------- assistant
export interface ChatSource {
  kind: string
  label: string
  detail: string
}

export interface ChatResponse {
  reply: string
  topic: string
  confidence: 'high' | 'medium' | 'low'
  used_context: ChatSource[]
  suggested_questions: string[]
  disclaimer: string
  created_at: string
}

export interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  topic?: string | null
  created_at: string
}

// ------------------------------------------------------------- weather
export interface WeatherPrefill {
  available: boolean
  city?: string
  values?: {
    temperature: number
    humidity: number
    rainfall: number
    rain_probability: number
    wind_speed: number
    weather_condition: WeatherCondition
  }
  notice?: string
  reason?: string
  not_filled?: string[]
  not_filled_note?: string
}

// -------------------------------------------------------------- system
export interface SystemStatus {
  app: string
  version: string
  python: string
  model_mode: string
  opencv_available: boolean
  models: {
    irrigation: IrrigationModelStatus & { label: string }
    disease: ImageModelStatus & { label: string }
    soil: ImageModelStatus & { label: string }
  }
  knowledge_base: Record<string, { loaded: boolean; schema_version?: string }>
  honesty_notice: string
}

/** Result of the pre-analysis image gate (see backend/app/ml/image_validation.py). */
export interface ImageValidation {
  isSugarcane: boolean
  confidence: number
  imageType:
    | 'sugarcane_plant'
    | 'other_plant'
    | 'plant_unverified'
    | 'soil_only'
    | 'soil'
    | 'not_soil'
    | 'plant_photo'
    | 'unclear_soil'
    | 'not_a_plant'
    | 'unclear'
  /** Headline for the notice, e.g. "Invalid Image - Please upload only a soil photo." */
  title: string
  message: string
  stage: 'A' | 'B'
  checked_by: 'rule_engine' | 'trained_model'
  notes: string[]
  scores?: Record<string, number>
  profile?: Record<string, number>
}
