import { getIdToken } from './auth'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// fetch wrapper that attaches the Firebase ID token to every request.
export async function apiFetch(path, options = {}) {
  const token = await getIdToken()
  const headers = { ...(options.headers || {}) }
  if (token) headers.Authorization = `Bearer ${token}`
  return fetch(`${API_BASE_URL}${path}`, { ...options, headers })
}

export { API_BASE_URL }
