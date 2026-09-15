// Тонкий клиент API. Токен приходит в ссылке из чат-бота: /app/?t=<token>
const params = new URLSearchParams(window.location.search)
export const TOKEN = params.get('t') || ''
export const ROLE = params.get('role') || 'student'

export class ApiError extends Error {
  constructor(message, hint, status) {
    super(message)
    this.hint = hint
    this.status = status
  }
}

async function call(path, { method = 'GET', body, token } = {}) {
  let resp
  try {
    resp = await fetch(path, {
      method,
      headers: {
        'content-type': 'application/json',
        ...(token ? { authorization: `Bearer ${token}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch (e) {
    throw new ApiError('Нет связи с сервисом', 'Проверьте интернет и повторите.', 0)
  }
  let data = null
  try {
    data = await resp.json()
  } catch (e) {
    data = null
  }
  if (!resp.ok) {
    const d = (data && data.detail) || data || {}
    throw new ApiError(d.message || `Ошибка ${resp.status}`, d.hint, resp.status)
  }
  return data
}

export const api = {
  meta: () => call('/api/meta'),
  fields: () => call('/api/catalog/fields'),
  session: (sid) => call(`/api/sessions/${sid}`, { token: TOKEN }),
  match: (sid, payload) => call(`/api/sessions/${sid}/match`, { method: 'POST', body: payload, token: TOKEN }),
  decide: (sid, payload) => call(`/api/sessions/${sid}/decision`, { method: 'POST', body: payload, token: TOKEN }),
  curatorAuth: (code) => call('/api/school/auth', { method: 'POST', body: { curator_code: code } }),
  analytics: (classCode, token) => call(`/api/school/${classCode}/analytics`, { token }),
}

// Идентификатор анкеты зашит в токен (base64url полезной нагрузки).
export function sessionIdFromToken(token) {
  try {
    const body = token.split('.')[0].replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(body + '==='.slice((body.length + 3) % 4))).sid
  } catch (e) {
    return ''
  }
}
