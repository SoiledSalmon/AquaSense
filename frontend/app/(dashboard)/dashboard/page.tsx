import React from 'react'
import { getMe } from '../../../lib/api/auth'

export const metadata = {
  title: 'Dashboard | AquaSense',
  description: 'AquaSense water quality and temperature telemetry dashboard.',
}

export default async function DashboardPage() {
  const user = await getMe()

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
            You are logged in. Phase 1 Auth integration is active. Telemetry charts, ThingSpeak stream connection, and sensor controls will be available in Phase 3.
          </p>
        </div>
      </div>

      {/* Quick Info Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="p-6 rounded-xl bg-slate-900/30 border border-slate-800 backdrop-blur-md space-y-3">
          <div className="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-400">ThingSpeak Channel</h4>
            <p className="text-lg font-bold text-slate-200 mt-1">
              {user.channel_id ? `ID: ${user.channel_id}` : 'Not configured'}
            </p>
          </div>
        </div>

        <div className="p-6 rounded-xl bg-slate-900/30 border border-slate-800 backdrop-blur-md space-y-3">
          <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.94.725l.548 2.2a1 1 0 01-.321.988l-1.305.98a10.582 10.582 0 004.872 4.872l.98-1.305a1 1 0 01.988-.321l2.2.548a1 1 0 01.725.94V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
            </svg>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-400">Alert Phone</h4>
            <p className="text-lg font-bold text-slate-200 mt-1">
              {user.phone ? user.phone : 'Not configured'}
            </p>
          </div>
        </div>

        <div className="p-6 rounded-xl bg-slate-900/30 border border-slate-800 backdrop-blur-md space-y-3">
          <div className="w-10 h-10 rounded-lg bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div>
            <h4 className="text-sm font-semibold text-slate-400">Session Role</h4>
            <p className="text-lg font-bold text-slate-200 mt-1 capitalize">
              {user.role || 'user'}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
