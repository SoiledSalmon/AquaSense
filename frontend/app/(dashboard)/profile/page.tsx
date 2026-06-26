import React from 'react'
import { getMe } from '../../../lib/api/auth'
import ProfileForm from '../../../components/profile/ProfileForm'

export const dynamic = 'force-dynamic'

export const metadata = {
  title: 'Profile Settings | AquaSense',
  description: 'Manage your profile and ThingSpeak integrations.',
}

export default async function ProfilePage() {
  const user = await getMe()

  return (
    <div className="space-y-6">
      <div className="border-b border-slate-800 pb-4">
        <h2 className="text-2xl font-extrabold text-slate-100">Profile Settings</h2>
        <p className="text-slate-400 text-sm mt-1">
          Update your account details and external IoT channel connections.
        </p>
      </div>

      <div className="bg-slate-900/20 border border-slate-800 rounded-xl p-6 backdrop-blur-md">
        <ProfileForm user={user} />
      </div>
    </div>
  )
}
