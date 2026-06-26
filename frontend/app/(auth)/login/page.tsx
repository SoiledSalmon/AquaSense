import React from 'react'
import LoginForm from '../../../components/auth/LoginForm'

export const metadata = {
  title: 'Sign In | AquaSense',
  description: 'Sign in to your AquaSense account to monitor your water system.',
}

export default function LoginPage() {
  return (
    <div>
      <LoginForm />
    </div>
  )
}
