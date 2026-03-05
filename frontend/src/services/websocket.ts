import type { WSEvent } from '@/types'

type EventHandler<T = unknown> = (data: T) => void

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

class WebSocketService {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private handlers: Map<string, Set<EventHandler>> = new Map()
  private isConnected = false
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null

  connect(projectId?: string): Promise<void> {
    return new Promise((resolve, reject) => {
      const url = projectId ? `${WS_URL}?project_id=${projectId}` : WS_URL

      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.isConnected = true
        this.reconnectAttempts = 0
        this.emit('connection_status', { connected: true })
        resolve()
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket disconnected:', event.reason)
        this.isConnected = false
        this.emit('connection_status', { connected: false })
        this.scheduleReconnect(projectId)
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.emit('error', { error })
        reject(error)
      }

      this.ws.onmessage = (event) => {
        try {
          const message: WSEvent = JSON.parse(event.data)
          this.handleMessage(message)
        } catch (e) {
          console.error('Failed to parse WebSocket message:', e)
        }
      }
    })
  }

  private handleMessage(event: WSEvent) {
    // Emit to specific event type handlers
    const handlers = this.handlers.get(event.type)
    if (handlers) {
      handlers.forEach((handler) => handler(event.data))
    }

    // Emit to all handlers
    const allHandlers = this.handlers.get('*')
    if (allHandlers) {
      allHandlers.forEach((handler) => handler(event))
    }
  }

  private emit(eventType: string, data: unknown) {
    const handlers = this.handlers.get(eventType)
    if (handlers) {
      handlers.forEach((handler) => handler(data))
    }
  }

  private scheduleReconnect(projectId?: string) {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnect attempts reached')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)

    this.reconnectTimer = setTimeout(() => {
      this.connect(projectId).catch(console.error)
    }, delay)
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.isConnected = false
  }

  subscribe<T = unknown>(eventType: string, handler: EventHandler<T>): () => void {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set())
    }
    this.handlers.get(eventType)!.add(handler as EventHandler)

    // Return unsubscribe function
    return () => {
      this.handlers.get(eventType)?.delete(handler as EventHandler)
    }
  }

  send(type: string, data: unknown) {
    if (this.ws && this.isConnected) {
      this.ws.send(JSON.stringify({ type, data }))
    } else {
      console.warn('WebSocket not connected, cannot send message')
    }
  }

  getConnectionStatus(): boolean {
    return this.isConnected
  }
}

export const wsService = new WebSocketService()
export default wsService
