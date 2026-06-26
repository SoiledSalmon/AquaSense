'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import { updateProfile } from '../../lib/api/auth'

interface ProfileFormProps {
  user: {
    full_name?: string | null
    channel_id?: string | null
    ts_api_key?: string | null
    phone?: string | null
  }
}

export default function ProfileForm({ user }: ProfileFormProps) {
  const router = useRouter()

  const [fullName, setFullName] = useState(user.full_name || '')
  const [channelId, setChannelId] = useState(user.channel_id || '')
  const [tsApiKey, setTsApiKey] = useState(user.ts_api_key || '')
  const [phone, setPhone] = useState(user.phone || '')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(false)
    setLoading(true)

    try {
      const updates: any = {}
      if (fullName !== (user.full_name || '')) updates.full_name = fullName || null
      if (channelId !== (user.channel_id || '')) updates.channel_id = channelId || null
      if (tsApiKey !== (user.ts_api_key || '')) updates.ts_api_key = tsApiKey || null
      if (phone !== (user.phone || '')) updates.phone = phone || null

      if (Object.keys(updates).length === 0) {
        throw new Error('No changes to save')
      }

      await updateProfile(updates)
      setSuccess(true)
      router.refresh()
    } catch (err: any) {
      setError(err.message || 'Failed to update profile')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6 max-w-xl">
      {error && (
        <div className="p-3.5 rounded-lg bg-red-950/40 border border-red-800/60 text-red-300 text-sm animate-in fade-in duration-200">
          {error}
        </div>
      )}

      {success && (
        <div className="p-3.5 rounded-lg bg-emerald-950/40 border border-emerald-800/60 text-emerald-300 text-sm animate-in fade-in duration-200">
          Profile updated successfully!
        </div>
      )}

      <div className="grid grid-cols-1 gap-6">
        {/* Full Name */}
        <div className="space-y-1.5">
          <label htmlFor="fullName" className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
            Full Name
          </label>
          <input
            id="fullName"
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full px-4 py-2.5 bg-slate-900/40 border border-slate-800 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all duration-200"
            placeholder="John Doe"
            disabled={loading}
          />
        </div>

        {/* Phone */}
        <div className="space-y-1.5">
          <label htmlFor="phone" className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
            Alert Phone Number
          </label>
          <input
            id="phone"
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="w-full px-4 py-2.5 bg-slate-900/40 border border-slate-800 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all duration-200"
            placeholder="+1234567890"
            disabled={loading}
          />
          <p className="text-[11px] text-slate-500">
            Used for SMS warning alerts in critical conditions. Include country code.
          </p>
        </div>

        {/* ThingSpeak Channel ID */}
        <div className="space-y-1.5">
          <label htmlFor="channelId" className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
            ThingSpeak Channel ID
          </label>
          <input
            id="channelId"
            type="text"
            value={channelId}
            onChange={(e) => setChannelId(e.target.value)}
            className="w-full px-4 py-2.5 bg-slate-900/40 border border-slate-800 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all duration-200"
            placeholder="1234567"
            disabled={loading}
          />
          <p className="text-[11px] text-slate-500">
            The unique channel ID where your ESP32 streams telemetry.
          </p>
        </div>

        {/* ThingSpeak Read API Key */}
        <div className="space-y-1.5">
          <label htmlFor="tsApiKey" className="block text-xs font-semibold uppercase tracking-wider text-slate-400">
            ThingSpeak Read API Key
          </label>
          <input
            id="tsApiKey"
            type="password"
            value={tsApiKey}
            onChange={(e) => setTsApiKey(e.target.value)}
            className="w-full px-4 py-2.5 bg-slate-900/40 border border-slate-800 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all duration-200"
            placeholder="••••••••••••••••"
            disabled={loading}
          />
          <p className="text-[11px] text-slate-500">
            Required if your ThingSpeak channel is private.
          </p>
        </div>
      </div>

      <div className="pt-2">
        <button
          type="submit"
          disabled={loading}
          className="relative group overflow-hidden px-6 py-2.5 bg-gradient-to-r from-blue-600 to-cyan-500 text-white font-medium rounded-lg hover:shadow-[0_0_15px_rgba(59,130,246,0.3)] disabled:opacity-50 disabled:shadow-none transition-all duration-300 cursor-pointer"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              Saving Changes...
            </span>
          ) : (
            'Save Changes'
          )}
        </button>
      </div>
    </form>
  )
}
