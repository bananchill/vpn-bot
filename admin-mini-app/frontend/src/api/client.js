import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Attach Telegram initData to every outgoing request so the backend
 * can authenticate the current Mini App user.
 */
api.interceptors.request.use((config) => {
  const initData = window.Telegram?.WebApp?.initData
  if (initData) {
    config.headers['X-Telegram-Init-Data'] = initData
  }
  return config
})

/**
 * Normalize API errors into a predictable shape.
 * Backend returns { detail: "..." } on HTTP errors.
 */
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'Неизвестная ошибка'

    // Preserve the original error but attach a readable message
    error.userMessage = message
    return Promise.reject(error)
  },
)

export default api
