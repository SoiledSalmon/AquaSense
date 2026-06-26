import { cookies } from 'next/headers'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function getHeaders() {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }

  if (typeof window === 'undefined') {
    try {
      const cookieStore = await cookies()
      const cookieString = cookieStore.toString()
      if (cookieString) {
        headers['Cookie'] = cookieString
      }
    } catch {
      // Ignore: cookies() can only be called in request context
    }
  }

  return headers
}

async function handleResponse(res: Response) {
  if (!res.ok) {
    let errorMsg = 'An error occurred'
    try {
      const data = await res.json()
      errorMsg = data.message || data.error || errorMsg
    } catch {
      // Fallback if response isn't JSON
    }
    throw new Error(errorMsg)
  }

  // Check for 204 No Content
  if (res.status === 204) {
    return null
  }

  const data = await res.json()

  // On the server side, forward Set-Cookie headers from FastAPI response to the client browser
  if (typeof window === 'undefined') {
    try {
      const setCookieHeaders = res.headers.getSetCookie()
      if (setCookieHeaders && setCookieHeaders.length > 0) {
        const cookieStore = await cookies()
        for (const cookieStr of setCookieHeaders) {
          const parts = cookieStr.split(';')
          const [nameValue, ...attrs] = parts
          const equalIdx = nameValue.indexOf('=')
          if (equalIdx !== -1) {
            const name = nameValue.slice(0, equalIdx).trim()
            const value = nameValue.slice(equalIdx + 1).trim()

            const options: any = {}
            attrs.forEach((attr) => {
              const [k, v] = attr.split('=').map((s) => s.trim())
              const key = k.toLowerCase()
              if (key === 'path') options.path = v
              else if (key === 'domain') options.domain = v
              else if (key === 'max-age') options.maxAge = parseInt(v, 10)
              else if (key === 'expires') options.expires = new Date(v)
              else if (key === 'httponly') options.httpOnly = true
              else if (key === 'secure') options.secure = true
              else if (key === 'samesite') {
                const val = v.toLowerCase()
                if (val === 'lax' || val === 'strict' || val === 'none') {
                  options.sameSite = val
                }
              }
            })

            cookieStore.set(name, value, options)
          }
        }
      }
    } catch {
      // Ignore: cookies() can only be called in request context
    }
  }

  return data
}

export async function signup(body: any) {
  const headers = await getHeaders()
  const res = await fetch(`${API_URL}/api/auth/signup`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  })
  return handleResponse(res)
}

export async function login(body: any) {
  const headers = await getHeaders()
  const res = await fetch(`${API_URL}/api/auth/login`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  })
  return handleResponse(res)
}

export async function logout() {
  const headers = await getHeaders()
  const res = await fetch(`${API_URL}/api/auth/logout`, {
    method: 'POST',
    headers,
  })

  // Propagate cookie deletion
  await handleResponse(res)

  if (typeof window === 'undefined') {
    try {
      const cookieStore = await cookies()
      cookieStore.delete('access_token')
      cookieStore.delete('refresh_token')
    } catch {
      // Ignore
    }
  }
}

export async function getMe() {
  const headers = await getHeaders()
  const res = await fetch(`${API_URL}/api/auth/me`, {
    method: 'GET',
    headers,
  })
  return handleResponse(res)
}

export async function updateProfile(body: any) {
  const headers = await getHeaders()
  const res = await fetch(`${API_URL}/api/auth/profile`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(body),
  })
  return handleResponse(res)
}
