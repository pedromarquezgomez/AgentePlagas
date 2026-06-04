import axios from 'axios'
import { getApps, initializeApp } from 'firebase/app'
import { getAuth } from 'firebase/auth'
import { ApiError } from './types'

// Inicializar Firebase Auth de la misma manera que en el resto del proyecto
const firebaseApp = getApps()[0] ?? initializeApp({
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY ?? '',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN ?? '',
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID ?? '',
})

export const auth = getAuth(firebaseApp)

const baseURL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export const client = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Interceptor de Request: Firebase Auth Token & Rutas Públicas
client.interceptors.request.use(
  async (config) => {
    const user = auth.currentUser
    const url = config.url || ''

    // Definir rutas públicas del backend
    const isPublicRoute =
      url === '/health' ||
      url.endsWith('/health') ||
      url === '/config/status' ||
      url.endsWith('/config/status') ||
      url === '/ready' ||
      url.endsWith('/ready')

    if (user) {
      try {
        const token = await user.getIdToken()
        config.headers.Authorization = `Bearer ${token}`
      } catch (err) {
        console.error('Error al obtener el ID Token de Firebase:', err)
      }
    } else if (!isPublicRoute) {
      // Bloquear localmente si no hay sesión y no es una ruta pública
      throw new ApiError('Usuario no autenticado. Petición bloqueada localmente.', 401, 'UNAUTHENTICATED')
    }

    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Interceptor de Response: Manejo de errores normalizado sin stack traces
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status || 500
      const data = error.response?.data
      let message = 'Ocurrió un error inesperado en el servidor.'
      let code = 'SERVER_ERROR'

      if (status === 401) {
        message = 'No autorizado. Por favor, inicia sesión.'
        code = 'UNAUTHORIZED'
      } else if (status === 403) {
        message = 'Acceso denegado. No tienes permisos suficientes.'
        code = 'FORBIDDEN'
      } else if (status === 404) {
        message = 'El recurso solicitado no fue encontrado.'
        code = 'NOT_FOUND'
      } else if (status === 422) {
        message = 'Los datos proporcionados no son válidos.'
        code = 'UNPROCESSABLE_ENTITY'
        if (data && typeof data === 'object' && 'detail' in data) {
          message = Array.isArray(data.detail)
            ? data.detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ')
            : String(data.detail)
        }
      } else if (status === 500) {
        message = 'Error interno en el servidor.'
        code = 'INTERNAL_SERVER_ERROR'
      } else if (error.code === 'ERR_NETWORK') {
        message = 'Error de red. Comprueba tu conexión a internet.'
        code = 'NETWORK_ERROR'
      }

      return Promise.reject(new ApiError(message, status, code))
    }

    if (error instanceof ApiError) {
      return Promise.reject(error)
    }

    return Promise.reject(new ApiError(error.message || 'Error inesperado', 500))
  }
)
