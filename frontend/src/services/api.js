import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Redirect to login on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api

// ── Auth ───────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
}

// ── Chat ───────────────────────────────────────────────────────────────────────
export const chatApi = {
  ask: (data) => api.post('/chat', data),
}

// ── Visa Cases ─────────────────────────────────────────────────────────────────
export const visaCasesApi = {
  list: () => api.get('/visa-cases'),
  create: (data) => api.post('/visa-cases', data),
  get: (id) => api.get(`/visa-cases/${id}`),
  delete: (id) => api.delete(`/visa-cases/${id}`),
}

// ── Checklists ─────────────────────────────────────────────────────────────────
export const checklistsApi = {
  generate: (data) => api.post('/checklists', data),
  list: () => api.get('/checklists'),
  get: (id) => api.get(`/checklists/${id}`),
  updateItem: (checklistId, itemId, data) =>
    api.patch(`/checklists/${checklistId}/items/${itemId}`, data),
  // Downloads the checklist as a file. format = 'pdf' | 'txt'.
  // responseType 'blob' keeps the binary intact and the JWT is sent via the
  // request interceptor (a plain <a href> link could not authenticate).
  export: (id, format) =>
    api.get(`/checklists/${id}/export`, { params: { format }, responseType: 'blob' }),
}

// ── Change Alerts ──────────────────────────────────────────────────────────────
export const alertsApi = {
  list: (params) => api.get('/change-alerts', { params }),
  getForCase: (caseId) => api.get(`/change-alerts/visa-cases/${caseId}`),
  markRead: (id) => api.patch(`/change-alerts/${id}/read`, { is_read: true }),
  runNow: () => api.post('/change-alerts/run'),
}

// ── Documents ──────────────────────────────────────────────────────────────────
export const documentsApi = {
  list: () => api.get('/documents'),
  get: (id) => api.get(`/documents/${id}`),
  scan: (formData) =>
    api.post('/documents/scan', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  fill: (docId, formData) =>
    api.post(`/documents/${docId}/fill`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  downloadUrl: (id) => `/api/v1/documents/${id}/download`,
}
