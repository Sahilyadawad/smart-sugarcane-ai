import axios, { AxiosError } from 'axios'
import type { ImageValidation } from '../types'

// 127.0.0.1 rather than localhost: on Windows `localhost` resolves to ::1 (IPv6)
// before 127.0.0.1, but uvicorn binds IPv4 only by default, so the browser's
// first connection attempt is refused.
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') || 'http://127.0.0.1:8000/api'

/** Uploaded images are served from the backend root, not under /api. */
export const MEDIA_BASE_URL =
  import.meta.env.VITE_MEDIA_BASE_URL?.replace(/\/$/, '') || ''

/**
 * Backend origin, i.e. the API base without its `/api` suffix.
 * Used for links to /docs and /redoc, which sit outside the API prefix. Deriving
 * it means a deployed build links to the deployed backend rather than to
 * localhost.
 */
export const BACKEND_ORIGIN = API_BASE_URL.replace(/\/api\/?$/, '')

const TOKEN_KEY = 'ssai.token'

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
})

api.interceptors.request.use((config) => {
  const token = tokenStore.get()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let onUnauthorized: (() => void) | null = null
export const setUnauthorizedHandler = (handler: () => void) => {
  onUnauthorized = handler
}

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    // 401 on anything except the login/register calls means the token expired.
    const url = error.config?.url ?? ''
    const isAuthAttempt = url.includes('/auth/login') || url.includes('/auth/register')
    if (error.response?.status === 401 && !isAuthAttempt) {
      tokenStore.clear()
      onUnauthorized?.()
    }
    return Promise.reject(error)
  },
)

/** Turn any axios failure into a single readable sentence for the UI. */
/** Pull the image-gate payload out of a 422 so the UI can render it properly. */
export function extractValidation(error: unknown): ImageValidation | null {
  if (!axios.isAxiosError(error)) return null
  const detail = error.response?.data?.detail
  if (detail && typeof detail === 'object' && 'validation' in detail) {
    return (detail as { validation: ImageValidation }).validation
  }
  return null
}

export function describeError(error: unknown, fallback = 'Something went wrong.'): string {
  if (axios.isAxiosError(error)) {
    const data = error.response?.data as
      | { detail?: string | { msg?: string }[]; problems?: string[] }
      | undefined

    if (data?.problems?.length) {
      return `${typeof data.detail === 'string' ? data.detail : 'Invalid input.'} ${data.problems.join('; ')}`
    }
    // The image gate returns detail as an object, not a string.
    if (data?.detail && typeof data.detail === 'object' && !Array.isArray(data.detail)) {
      const detail = data.detail as { message?: string }
      if (detail.message) return detail.message
    }
    if (typeof data?.detail === 'string') {
      return data.detail
    }
    if (Array.isArray(data?.detail)) {
      return data.detail.map((item) => item.msg ?? String(item)).join('; ')
    }
    if (error.code === 'ECONNABORTED') {
      return 'The request timed out. The backend may still be starting up.'
    }
    if (!error.response) {
      return `Cannot reach the backend at ${API_BASE_URL}. Is it running? Start it with: uvicorn app.main:app --reload`
    }
    return error.message || fallback
  }
  if (error instanceof Error) return error.message
  return fallback
}

/** Build a displayable URL for an image path returned by the API. */
export function mediaUrl(path?: string | null): string {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return `${MEDIA_BASE_URL}${path}`
}
