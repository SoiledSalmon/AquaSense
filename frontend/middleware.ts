import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const hasAccessToken = request.cookies.has('access_token')
  const hasRefreshToken = request.cookies.has('refresh_token')
  const isAuthenticated = hasAccessToken || hasRefreshToken

  const { pathname } = request.nextUrl

  // Protected paths
  const isProtectedPath = pathname.startsWith('/dashboard') || pathname.startsWith('/profile')
  // Auth pages
  const isAuthPage = pathname.startsWith('/login') || pathname.startsWith('/signup')

  if (isProtectedPath && !isAuthenticated) {
    const loginUrl = new URL('/login', request.url)
    loginUrl.searchParams.set('redirectTo', pathname)
    return NextResponse.redirect(loginUrl)
  }

  if (isAuthPage) {
    if (request.nextUrl.searchParams.has('clear')) {
      const response = NextResponse.next()
      response.cookies.delete('access_token')
      response.cookies.delete('refresh_token')
      return response
    }
    if (isAuthenticated) {
      return NextResponse.redirect(new URL('/dashboard', request.url))
    }
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - static images/files
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
}
