import React from 'react'
import { redirect } from 'next/navigation'
import { getMe } from '../../../lib/api/auth'
import LiveDashboard from '../../../components/dashboard/LiveDashboard'

export const dynamic = 'force-dynamic'

export const metadata = {
  title: 'Dashboard | AquaSense',
  description: 'AquaSense water quality and temperature telemetry dashboard.',
}

export default async function DashboardPage() {
  let user
  try {
    user = await getMe()
  } catch (err) {
    redirect('/login?clear=true')
  }

  return (
    <div className="space-y-6">
      {/* Welcome Card */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/40 p-6 md:p-8 backdrop-blur-md">
        <div className="absolute -right-16 -top-16 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl" />
        <div className="relative z-10 space-y-2">
          <h2 className="text-2xl md:text-3xl font-extrabold text-slate-100">
            Welcome back, {user.full_name || 'AquaSensor'}!
          </h2>
          <p className="text-slate-400 text-sm md:text-base max-w-xl">
            Live telemetry charts, ThingSpeak MQTT streaming connectivity, and real-time anomaly alerts are fully operational.
          </p>
        </div>
      </div>

      {/* Live Telemetry and Charts Dashboard */}
      <LiveDashboard user={user} />
    </div>
  )
}
