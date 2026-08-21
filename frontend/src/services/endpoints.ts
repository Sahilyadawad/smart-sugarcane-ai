/** Typed wrappers around every backend endpoint the UI uses. */

import { api } from './api'
import type {
  AuthResponse,
  ChatMessage,
  ChatResponse,
  DashboardSummary,
  FertilizerRecommendation,
  HistoryDetail,
  HistoryPage,
  ImageModelStatus,
  IrrigationChartPoint,
  IrrigationInput,
  IrrigationModelStatus,
  IrrigationResult,
  PlantAnalysisResult,
  PlantTrend,
  SoilAnalysisResult,
  SystemStatus,
  User,
  VarietyRecommendation,
  WeatherPrefill,
} from '../types'

// ---------------------------------------------------------------- auth
export const authApi = {
  register: (payload: {
    name: string
    email: string
    password: string
    phone?: string
    farm_location?: string
  }) => api.post<AuthResponse>('/auth/register', payload).then((r) => r.data),

  login: (payload: { email: string; password: string }) =>
    api.post<AuthResponse>('/auth/login', payload).then((r) => r.data),

  me: () => api.get<User>('/auth/me').then((r) => r.data),

  updateProfile: (payload: Partial<User>) =>
    api.patch<User>('/auth/me', payload).then((r) => r.data),

  changePassword: (payload: { current_password: string; new_password: string }) =>
    api.post<{ detail: string }>('/auth/me/password', payload).then((r) => r.data),

  forgotPassword: (email: string) =>
    api.post<{ detail: string }>('/auth/forgot-password', { email }).then((r) => r.data),
}

// ----------------------------------------------------------- dashboard
export const dashboardApi = {
  summary: () => api.get<DashboardSummary>('/dashboard/summary').then((r) => r.data),
}

// ---------------------------------------------------------- irrigation
export const irrigationApi = {
  predict: (payload: IrrigationInput) =>
    api.post<IrrigationResult>('/irrigation/predict', payload).then((r) => r.data),

  chart: (limit = 10) =>
    api.get<IrrigationChartPoint[]>('/irrigation/chart', { params: { limit } }).then((r) => r.data),

  modelStatus: () =>
    api.get<IrrigationModelStatus>('/irrigation/model-status').then((r) => r.data),

  options: () => api.get<Record<string, unknown>>('/irrigation/options').then((r) => r.data),

  simulateSoilMoisture: (payload: {
    days_since_irrigation: number
    starting_moisture: number
    soil_type: string
    growth_stage: string
    temperature: number
    humidity: number
    wind_speed: number
    weather_condition: string
    rainfall_since: number
  }) =>
    api
      .post<Record<string, number | string>>('/irrigation/simulate-soil-moisture', payload)
      .then((r) => r.data),
}

// --------------------------------------------------------------- plant
export const plantApi = {
  analyze: (file: File, growthStage?: string, notes?: string) => {
    const form = new FormData()
    form.append('file', file)
    if (growthStage) form.append('growth_stage', growthStage)
    if (notes) form.append('notes', notes)
    form.append('save', 'true')
    return api
      .post<PlantAnalysisResult>('/plants/analyze', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },

  trend: (limit = 12) =>
    api.get<PlantTrend>('/plants/trend', { params: { limit } }).then((r) => r.data),

  modelStatus: () => api.get<ImageModelStatus>('/plants/model-status').then((r) => r.data),
}

// ---------------------------------------------------------------- soil
export const soilApi = {
  analyze: (
    file: File,
    context: {
      region?: string
      district?: string
      climate?: string
      irrigation_available?: boolean
      water_availability?: string
      planting_season?: string
      soil_type_override?: string
    },
  ) => {
    const form = new FormData()
    form.append('file', file)
    Object.entries(context).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        form.append(key, String(value))
      }
    })
    form.append('save', 'true')
    return api
      .post<SoilAnalysisResult>('/soil/analyze', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },

  modelStatus: () => api.get<ImageModelStatus>('/soil/model-status').then((r) => r.data),
}

// ------------------------------------------------------ recommendations
export const recommendationApi = {
  variety: (payload: {
    soil_type: string
    region?: string | null
    district?: string | null
    climate?: string
    irrigation_available?: boolean
    water_availability?: string
    planting_season?: string
    limit?: number
  }) => api.post<VarietyRecommendation>('/recommendations/variety', payload).then((r) => r.data),

  fertilizer: (payload: {
    growth_stage: string
    soil_type: string
    water_availability?: string
    irrigation_available?: boolean
    plant_condition?: string | null
    organic_matter_appearance?: string | null
    nitrogen_kg_ha?: number | null
    phosphorus_kg_ha?: number | null
    potassium_kg_ha?: number | null
    soil_ph?: number | null
  }) =>
    api.post<FertilizerRecommendation>('/recommendations/fertilizer', payload).then((r) => r.data),

  varieties: () => api.get<Record<string, unknown>>('/recommendations/varieties').then((r) => r.data),
}

// ------------------------------------------------------------- history
export const historyApi = {
  list: (params: { kind?: string; page?: number; page_size?: number } = {}) =>
    api.get<HistoryPage>('/history', { params }).then((r) => r.data),

  detail: (kind: string, id: number) =>
    api.get<HistoryDetail>(`/history/${kind}/${id}`).then((r) => r.data),

  remove: (kind: string, id: number) =>
    api.delete<{ detail: string }>(`/history/${kind}/${id}`).then((r) => r.data),

  clearAll: () => api.delete<{ detail: string }>('/history').then((r) => r.data),
}

// ----------------------------------------------------------- assistant
export const assistantApi = {
  chat: (message: string, language = 'en') =>
    api.post<ChatResponse>('/assistant/chat', { message, language }).then((r) => r.data),

  history: (limit = 50) =>
    api.get<ChatMessage[]>('/assistant/history', { params: { limit } }).then((r) => r.data),

  clear: () => api.delete<{ detail: string }>('/assistant/history').then((r) => r.data),

  info: () => api.get<Record<string, unknown>>('/assistant/info').then((r) => r.data),
}

// ------------------------------------------------------------- weather
export const weatherApi = {
  prefill: (city?: string) =>
    api
      .get<WeatherPrefill>('/weather/irrigation-prefill', { params: city ? { city } : {} })
      .then((r) => r.data),

  current: (city?: string) =>
    api
      .get<Record<string, unknown>>('/weather/current', { params: city ? { city } : {} })
      .then((r) => r.data),
}

// -------------------------------------------------------------- system
export const systemApi = {
  status: () => api.get<SystemStatus>('/system/status').then((r) => r.data),
  health: () => api.get<{ status: string }>('/system/health').then((r) => r.data),
}
