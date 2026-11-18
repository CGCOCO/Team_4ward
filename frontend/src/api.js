import axios from 'axios'

export const API_BASE_URL = 'http://localhost:8000'
export const TOKEN_KEY = 'safety_ai_access_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export const api = axios.create({
  baseURL: API_BASE_URL,
})

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// AI 어드바이저 SSE 스트림: onEvent(eventName, data) 로 progress/sources/delta/done/error 전달
export async function streamAdvisorChat(body, onEvent, signal) {
  const token = getToken()
  const response = await fetch(`${API_BASE_URL}/api/v1/advisor/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
    signal,
  })
  if (!response.ok || !response.body) {
    const payload = await response.json().catch(() => ({}))
    const error = new Error(payload.detail ?? '요청에 실패했습니다.')
    error.status = response.status
    throw error
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done })
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() ?? ''
    for (const block of blocks) {
      const event = block.match(/^event: (.+)$/m)?.[1]
      const data = block.match(/^data: (.+)$/m)?.[1]
      if (event && data) onEvent(event, JSON.parse(data))
    }
    if (done) break
  }
}
