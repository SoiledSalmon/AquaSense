import React, { Suspense } from 'react'
import LoginForm from '../../../components/auth/LoginForm'

export const metadata = {
  title: 'Sign In | AquaSense',
  description: 'Sign in to your AquaSense account to monitor your water system.',
}

export default function LoginPage() {
  return (
    <div>
      <Suspense fallback={<div className="text-slate-400 text-sm text-center py-4">Loading login form...</div>}>
        <LoginForm />
      </Suspense>
    </div>
  )
}
