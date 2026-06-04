import { onMounted, onUnmounted } from 'vue'
import { auth } from '../api/client'

export function useEventStream(onEvent: (event: any) => void) {
  let eventSource: EventSource | null = null
  let reconnectTimeout: ReturnType<typeof setTimeout> | null = null

  async function connect() {
    try {
      const user = auth.currentUser
      if (!user) {
        // Si no hay usuario logueado en este momento, reintentar en 2 segundos
        reconnectTimeout = setTimeout(connect, 2000)
        return
      }
      
      const token = await user.getIdToken()
      const baseUrl = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'
      const url = `${baseUrl}/events/stream?token=${encodeURIComponent(token)}`

      eventSource = new EventSource(url)

      eventSource.onmessage = (e) => {
        try {
          const eventData = JSON.parse(e.data)
          onEvent(eventData)
        } catch (err) {
          console.error('Error parsing event stream message:', err)
        }
      }

      eventSource.onerror = () => {
        console.warn('SSE connection lost. Reconnecting in 5 seconds...')
        cleanup()
        reconnectTimeout = setTimeout(connect, 5000)
      }
    } catch (err) {
      console.error('Failed to establish EventSource connection:', err)
      cleanup()
      reconnectTimeout = setTimeout(connect, 5000)
    }
  }

  function cleanup() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
    if (reconnectTimeout) {
      clearTimeout(reconnectTimeout)
      reconnectTimeout = null
    }
  }

  onMounted(() => {
    void connect()
  })

  onUnmounted(() => {
    cleanup()
  })

  return {
    reconnect: () => {
      cleanup()
      void connect()
    }
  }
}
