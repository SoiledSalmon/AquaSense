"use client"

import React, { useEffect, useState, useRef } from 'react'
import {
  Activity,
  Wifi,
  WifiOff,
  AlertTriangle,
  CheckCircle2,
  Droplets,
  Filter,
  TrendingUp,
  Clock,
  RefreshCw,
  Info,
  Bell,
  Check
} from 'lucide-react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts'

import { getLatestReading, getReadingsHistory, getSSEStreamUrl } from '../../lib/api/readings'
import { getAlerts, acknowledgeAlert } from '../../lib/api/alerts'

interface User {
  id: string
  email: string
  full_name?: string
  role?: string
  channel_id?: string
  phone?: string
}

interface Reading {
  id?: string
  timestamp: string
  ph: number | null
  tds: number | null
  turbidity: number | null
  wqi_score: number | null
  label: string | null
}

interface Alert {
  id: string
  timestamp: string
  message: string
  is_read: boolean
  severity?: 'info' | 'warning' | 'critical'
  category?: string
  is_acknowledged?: boolean
  is_resolved?: boolean
  recommendation?: string
}

export default function LiveDashboard({ user }: { user: User }) {
  // --- State ---
  const [connectionStatus, setConnectionStatus] = useState<'CONNECTED' | 'RECONNECTING' | 'DISCONNECTED'>('DISCONNECTED')
  const [latestReading, setLatestReading] = useState<Reading | null>(null)
  const [historyData, setHistoryData] = useState<any[]>([])
  const [range, setRange] = useState<'24h' | '7d' | '30d'>('24h')
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [activeTab, setActiveTab] = useState<'wqi' | 'ph' | 'tds' | 'turbidity'>('wqi')
  const [loading, setLoading] = useState(true)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [alertsFilter, setAlertsFilter] = useState<'unacknowledged' | 'all' | 'resolved'>('unacknowledged')
  const [alertsLoading, setAlertsLoading] = useState(false)

  // Keep a reference to range for the SSE callback
  const rangeRef = useRef(range)
  useEffect(() => {
    rangeRef.current = range
  }, [range])

  const alertsFilterRef = useRef(alertsFilter)
  useEffect(() => {
    alertsFilterRef.current = alertsFilter
  }, [alertsFilter])

  // --- Initial Data Load ---
  useEffect(() => {
    async function initData() {
      try {
        setLoading(true)
        const latestRes = await getLatestReading()
        if (latestRes && latestRes.reading) {
          setLatestReading(latestRes.reading)
        }

        const historyRes = await getReadingsHistory('24h')
        if (historyRes && historyRes.data) {
          setHistoryData(historyRes.data)
        }

        const alertsRes = await getAlerts('unacknowledged')
        if (alertsRes && alertsRes.alerts) {
          setAlerts(alertsRes.alerts)
        }
      } catch (err: any) {
        console.error('Failed to fetch initial telemetry data:', err)
        setError(err.message || 'Failed to load telemetry')
      } finally {
        setLoading(false)
      }
    }

    if (user.channel_id) {
      initData()
    } else {
      setLoading(false)
    }
  }, [user.channel_id])

  const fetchFilteredAlerts = async (status: 'unacknowledged' | 'all' | 'resolved') => {
    try {
      setAlertsLoading(true)
      const res = await getAlerts(status)
      if (res && res.alerts) {
        setAlerts(res.alerts)
      }
    } catch (err) {
      console.error('Failed to fetch filtered alerts:', err)
    } finally {
      setAlertsLoading(false)
    }
  }

  // Effect to load alerts when filter changes
  useEffect(() => {
    if (user.channel_id && !loading) {
      fetchFilteredAlerts(alertsFilter)
    }
  }, [alertsFilter, user.channel_id])

  // --- Range Changes ---
  const handleRangeChange = async (newRange: '24h' | '7d' | '30d') => {
    setRange(newRange)
    try {
      setHistoryLoading(true)
      const res = await getReadingsHistory(newRange)
      if (res && res.data) {
        setHistoryData(res.data)
      }
    } catch (err: any) {
      console.error('Failed to fetch historical readings:', err)
    } finally {
      setHistoryLoading(false)
    }
  }

  // --- SSE Stream Connection ---
  useEffect(() => {
    if (!user.channel_id) return

    let eventSource: EventSource | null = null

    function connectSSE() {
      const sseUrl = getSSEStreamUrl()
      console.log('Establishing EventSource connection to:', sseUrl)
      
      eventSource = new EventSource(sseUrl, { withCredentials: true })

      eventSource.onopen = () => {
        console.log('SSE connection successfully opened')
        setConnectionStatus('CONNECTED')
      }

      eventSource.onerror = (err) => {
        console.warn('SSE connection encountered an error, reconnecting...', err)
        setConnectionStatus('RECONNECTING')
      }

      // Live Telemetry updates
      eventSource.addEventListener('reading_update', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as Reading
          console.log('Received live reading update:', data)
          
          setLatestReading(data)

          // Update history in-memory if range is 24h
          if (rangeRef.current === '24h') {
            setHistoryData((prev) => {
              // Avoid duplicate inserts for the exact same timestamp
              const exists = prev.some((item) => item.bucket === data.timestamp)
              if (exists) return prev

              const newPoint = {
                bucket: data.timestamp,
                avg_ph: data.ph,
                avg_tds: data.tds,
                avg_turbidity: data.turbidity,
                avg_wqi: data.wqi_score,
                user_id: user.id
              }
              const updated = [...prev, newPoint]
              // Keep rolling window of 24 hourly buckets
              if (updated.length > 24) {
                return updated.slice(updated.length - 24)
              }
              return updated
            })
          }
        } catch (err) {
          console.error('Failed to parse reading update event:', err)
        }
      })

      // Live Warning Alert updates
      eventSource.addEventListener('alert_new', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data) as Alert
          console.log('Received live alert:', data)
          setAlerts((prev) => {
            // Avoid duplicate alerts
            if (prev.some((a) => a.id === data.id)) return prev
            if (alertsFilterRef.current === 'resolved') return prev
            return [data, ...prev]
          })
        } catch (err) {
          console.error('Failed to parse alert event:', err)
        }
      })

      eventSource.addEventListener('heartbeat', () => {
        // Heartbeat kept connection alive
      })
    }

    connectSSE()

    return () => {
      if (eventSource) {
        console.log('Closing EventSource connection')
        eventSource.close()
        setConnectionStatus('DISCONNECTED')
      }
    }
  }, [user.channel_id, user.id])

  // --- Alert Acknowledgement ---
  const dismissAlert = async (alertId: string) => {
    try {
      await acknowledgeAlert(alertId)
      if (alertsFilter === 'unacknowledged') {
        setAlerts((prev) => prev.filter((a) => a.id !== alertId))
      } else {
        setAlerts((prev) =>
          prev.map((a) =>
            a.id === alertId
              ? { ...a, is_acknowledged: true, is_read: true }
              : a
          )
        )
      }
    } catch (err) {
      console.error('Failed to acknowledge alert:', err)
    }
  }

  // --- WQI Display Configuration ---
  const getWQIDetails = (wqi: number | null) => {
    if (wqi === null) return { text: 'N/A', color: 'text-slate-500', bg: 'bg-slate-500/10', border: 'border-slate-800', ambient: 'bg-slate-500/5' }
    if (wqi >= 95) return { text: 'Excellent', color: 'text-cyan-400', bg: 'bg-cyan-500/10', border: 'border-cyan-500/30', ambient: 'bg-cyan-500/10' }
    if (wqi >= 80) return { text: 'Good', color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', ambient: 'bg-emerald-500/10' }
    if (wqi >= 65) return { text: 'Fair', color: 'text-amber-400', bg: 'bg-amber-500/10', border: 'border-amber-500/30', ambient: 'bg-amber-500/10' }
    return { text: 'Unsafe', color: 'text-rose-400', bg: 'bg-rose-500/10', border: 'border-rose-500/30', ambient: 'bg-rose-500/10' }
  }

  const getLabelDetails = (label: string | null) => {
    const l = (label || '').toLowerCase()
    if (l === 'safe') return { text: 'Potable / Safe', color: 'text-cyan-400', desc: 'Meets strict drinking water guidelines.' }
    if (l === 'borderline') return { text: 'Borderline / Caution', color: 'text-amber-400', desc: 'Elevated contaminants. Boil or filter before use.' }
    if (l === 'unsafe') return { text: 'Unsafe / Contaminated', color: 'text-rose-400', desc: 'High contamination! Not safe for ingestion.' }
    return { text: 'Unknown', color: 'text-slate-400', desc: 'Insufficient sensor calibration data.' }
  }

  const getRecommendation = (label: string | null, ph: number | null, tds: number | null, turbidity: number | null) => {
    const l = (label || '').toLowerCase()
    if (l === 'safe') {
      return 'Water parameters reside in the optimal range. Safe for consumption, hygiene, and general household usage.'
    }
    if (l === 'borderline') {
      let issues = []
      if (ph && (ph < 6.5 || ph > 8.5)) issues.push(`abnormal pH (${ph})`)
      if (tds && tds > 300) issues.push(`elevated TDS (${tds} ppm)`)
      if (turbidity && turbidity > 5) issues.push(`raised turbidity (${turbidity} NTU)`)
      return `Water is borderline safe due to ${issues.join(', ') || 'minor anomalies'}. Boiling and carbon filtration are recommended before consumption.`
    }
    if (l === 'unsafe') {
      let critical = []
      if (ph && (ph < 6.0 || ph > 9.0)) critical.push(`highly acidic/alkaline pH of ${ph}`)
      if (tds && tds > 600) critical.push(`critical TDS of ${tds} ppm`)
      if (turbidity && turbidity > 15) critical.push(`extreme turbidity of ${turbidity} NTU`)
      return `CRITICAL: Water contains toxic levels of ${critical.join(' and ') || 'pollutants'}. Do not consume. Service your active filtration membrane immediately.`
    }
    return 'Waiting for active IoT sensor readings to establish machine-learning safety analysis...'
  }

  // --- Telemetry Cards Configuration ---
  const phZone = (ph: number | null) => {
    if (ph === null) return 'text-slate-500'
    if (ph >= 6.5 && ph <= 8.5) return 'text-emerald-400'
    return 'text-rose-400'
  }

  const tdsZone = (tds: number | null) => {
    if (tds === null) return 'text-slate-500'
    if (tds < 300) return 'text-cyan-400'
    if (tds < 600) return 'text-amber-400'
    return 'text-rose-400'
  }

  const turbidityZone = (turb: number | null) => {
    if (turb === null) return 'text-slate-500'
    if (turb < 5.0) return 'text-emerald-400'
    if (turb < 15.0) return 'text-amber-400'
    return 'text-rose-400'
  }

  // --- History Chart Formatting ---
  const formatXAxis = (tickItem: string) => {
    if (!tickItem) return ''
    try {
      const date = new Date(tickItem)
      if (range === '24h') {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
      }
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
    } catch {
      return tickItem
    }
  }

  const chartTheme = {
    wqi: { stroke: '#22d3ee', fill: 'url(#colorWqi)', label: 'WQI Score', key: 'avg_wqi' },
    ph: { stroke: '#34d399', fill: 'url(#colorPh)', label: 'pH Level', key: 'avg_ph' },
    tds: { stroke: '#fbbf24', fill: 'url(#colorTds)', label: 'TDS (ppm)', key: 'avg_tds' },
    turbidity: { stroke: '#a78bfa', fill: 'url(#colorTurb)', label: 'Turbidity (NTU)', key: 'avg_turbidity' }
  }

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 space-y-4">
        <RefreshCw className="w-8 h-8 text-blue-500 animate-spin" />
        <p className="text-slate-400 text-sm">Synchronizing with live telemetry stream...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6 rounded-2xl border border-red-900/30 bg-red-950/20 text-center space-y-3">
        <AlertTriangle className="w-10 h-10 text-red-500 mx-auto" />
        <h3 className="text-lg font-bold text-slate-200">Failed to establish telemetry connection</h3>
        <p className="text-red-300 text-sm max-w-md mx-auto">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="mt-2 px-4 py-2 bg-red-500/10 border border-red-500/20 hover:bg-red-500/20 text-red-400 rounded-lg text-xs font-semibold transition"
        >
          Retry Connection
        </button>
      </div>
    )
  }

  if (!user.channel_id) {
    return (
      <div className="p-8 rounded-2xl border border-slate-800 bg-slate-900/40 text-center space-y-4 max-w-md mx-auto">
        <Activity className="w-12 h-12 text-slate-600 mx-auto" />
        <h3 className="text-lg font-bold text-slate-200">No IoT Channel Configured</h3>
        <p className="text-slate-400 text-sm">
          Please navigate to your Profile Settings page to configure your ThingSpeak Channel ID and API Keys to receive sensor data.
        </p>
      </div>
    )
  }

  const wqiVal = latestReading?.wqi_score !== undefined ? latestReading.wqi_score : null
  const wqiDetails = getWQIDetails(wqiVal)
  const safetyDetails = getLabelDetails(latestReading?.label || null)

  return (
    <div className="space-y-6">
      {/* ── SSE Connection Status Banner ─────────────────────────── */}
      <div className="flex items-center justify-between p-4 rounded-xl border border-slate-800 bg-slate-900/20 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center">
            {connectionStatus === 'CONNECTED' ? (
              <>
                <span className="animate-ping absolute inline-flex h-3.5 w-3.5 rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500" />
              </>
            ) : connectionStatus === 'RECONNECTING' ? (
              <>
                <span className="animate-ping absolute inline-flex h-3.5 w-3.5 rounded-full bg-amber-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500" />
              </>
            ) : (
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-rose-500" />
            )}
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-400">Stream Connection</p>
            <p className="text-sm font-bold text-slate-200">
              {connectionStatus === 'CONNECTED'
                ? 'Connected (Live Stream)'
                : connectionStatus === 'RECONNECTING'
                ? 'Reconnecting (Network Blip)'
                : 'Disconnected'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Clock className="w-3.5 h-3.5" />
          <span>Last Ingest: {latestReading ? new Date(latestReading.timestamp).toLocaleTimeString() : 'Never'}</span>
        </div>
      </div>

      {/* ── Alerts & Notification Center ─────────────────────────── */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-6 space-y-6 backdrop-blur-md">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Bell className="w-5 h-5 text-blue-400" />
              {alerts.filter(a => !a.is_acknowledged).length > 0 && (
                <span className="absolute -top-1 -right-1 flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-rose-500"></span>
                </span>
              )}
            </div>
            <div>
              <h3 className="font-bold text-slate-200 text-base">Alerts & Notification Center</h3>
              <p className="text-xs text-slate-400">
                {alerts.filter(a => !a.is_acknowledged).length} active warnings detected
              </p>
            </div>
          </div>

          {/* Filter Tabs */}
          <div className="flex rounded-lg bg-slate-950 p-1 border border-slate-800 text-xs self-start sm:self-auto">
            {(['unacknowledged', 'resolved', 'all'] as const).map((filter) => (
              <button
                key={filter}
                onClick={() => setAlertsFilter(filter)}
                className={`px-3 py-1.5 rounded-md font-semibold transition capitalize ${
                  alertsFilter === filter ? 'bg-slate-800 text-slate-100' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {filter === 'unacknowledged' ? 'Active' : filter}
              </button>
            ))}
          </div>
        </div>

        {/* Alerts List */}
        {alertsLoading ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="w-6 h-6 text-blue-500 animate-spin" />
          </div>
        ) : alerts.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 space-y-3 border border-dashed border-slate-800 rounded-xl bg-slate-950/10">
            <CheckCircle2 className="w-10 h-10 text-emerald-500" />
            <div className="text-center">
              <p className="text-sm font-semibold text-slate-300">All Systems Healthy</p>
              <p className="text-xs text-slate-500 max-w-sm mt-1">
                No alerts detected. All water parameters are within standard operating thresholds.
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-3 max-h-[380px] overflow-y-auto pr-1">
            {alerts.map((alert) => {
              const sev = alert.severity || 'info'
              const isCrit = sev === 'critical'
              const isWarn = sev === 'warning'
              
              const severityTheme = isCrit 
                ? { bg: 'bg-rose-500/10 border-rose-500/20', text: 'text-rose-400', icon: <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" /> }
                : isWarn
                ? { bg: 'bg-amber-500/10 border-amber-500/20', text: 'text-amber-400', icon: <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" /> }
                : { bg: 'bg-blue-500/10 border-blue-500/20', text: 'text-blue-400', icon: <Info className="w-5 h-5 text-blue-400 shrink-0 mt-0.5" /> }

              return (
                <div
                  key={alert.id}
                  className={`flex flex-col md:flex-row md:items-start justify-between gap-4 p-4 rounded-xl border ${severityTheme.bg} backdrop-blur-md transition-all duration-300`}
                >
                  <div className="flex gap-3 items-start">
                    {severityTheme.icon}
                    <div className="space-y-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`text-xs font-extrabold uppercase px-2 py-0.5 rounded bg-slate-900 border border-slate-800 ${severityTheme.text}`}>
                          {sev}
                        </span>
                        <span className="text-xs font-bold text-slate-400 capitalize">
                          {alert.category || 'general'}
                        </span>
                        <span className="text-[10px] text-slate-500">
                          {new Date(alert.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <h4 className="text-sm font-bold text-slate-200">{alert.message}</h4>
                      {alert.recommendation && (
                        <p className="text-xs text-slate-400 leading-relaxed pt-1 border-t border-slate-800/40">
                          <span className="font-bold text-slate-300">Recommendation: </span>
                          {alert.recommendation}
                        </p>
                      )}
                    </div>
                  </div>
                  
                  {!alert.is_acknowledged && (
                    <button
                      onClick={() => dismissAlert(alert.id)}
                      className="flex items-center gap-1.5 self-end md:self-start px-3.5 py-1.5 bg-slate-950/60 border border-slate-800 hover:border-slate-700 hover:bg-slate-900 text-xs font-bold text-slate-300 hover:text-white rounded-lg transition"
                    >
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Acknowledge</span>
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* ── Radial WQI Score & ML Analysis ───────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Radial WQI Box */}
        <div className={`relative overflow-hidden rounded-2xl border ${wqiDetails.border} bg-slate-900/40 p-6 flex flex-col items-center justify-center text-center backdrop-blur-md`}>
          {/* Ambient glow */}
          <div className={`absolute -inset-10 ${wqiDetails.ambient} rounded-full blur-3xl pointer-events-none`} />

          <h3 className="text-sm font-semibold tracking-wider uppercase text-slate-400 mb-6 relative z-10">
            Water Quality Index (WQI)
          </h3>

          <div className="relative w-36 h-36 flex items-center justify-center mb-4 z-10">
            {/* SVG Progress Circle */}
            <svg className="w-full h-full transform -rotate-90">
              <circle
                cx="72"
                cy="72"
                r="64"
                className="stroke-slate-800"
                strokeWidth="10"
                fill="transparent"
              />
              <circle
                cx="72"
                cy="72"
                r="64"
                className="transition-all duration-1000 ease-out"
                strokeWidth="10"
                fill="transparent"
                strokeLinecap="round"
                strokeDasharray={2 * Math.PI * 64}
                strokeDashoffset={2 * Math.PI * 64 * (1 - (wqiVal !== null ? Math.min(Math.max(wqiVal, 0), 100) : 0) / 100)}
                stroke={wqiVal !== null ? (wqiVal >= 95 ? '#22d3ee' : wqiVal >= 80 ? '#10b981' : wqiVal >= 65 ? '#f59e0b' : '#f43f5e') : '#475569'}
              />
            </svg>
            <div className="absolute flex flex-col items-center justify-center">
              <span className="text-4xl font-extrabold text-slate-100">
                {wqiVal !== null ? Math.round(wqiVal) : '—'}
              </span>
              <span className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 mt-1 rounded ${wqiDetails.bg} ${wqiDetails.color}`}>
                {wqiDetails.text}
              </span>
            </div>
          </div>
        </div>

        {/* Machine Learning Recommendations */}
        <div className="lg:col-span-2 rounded-2xl border border-slate-800 bg-slate-900/40 p-6 flex flex-col justify-between backdrop-blur-md">
          <div className="space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-400" />
                <h3 className="font-bold text-slate-200 text-base">AquaSense ML Potability Analysis</h3>
              </div>
              <span className={`text-xs font-bold ${safetyDetails.color}`}>
                {safetyDetails.text}
              </span>
            </div>
            <div className="space-y-2">
              <p className="text-sm text-slate-300 font-medium">
                {safetyDetails.desc}
              </p>
              <p className="text-sm text-slate-400 leading-relaxed">
                {getRecommendation(latestReading?.label || null, latestReading?.ph || null, latestReading?.tds || null, latestReading?.turbidity || null)}
              </p>
            </div>
          </div>

          <div className="mt-4 p-3.5 rounded-xl bg-slate-950/40 border border-slate-800/60 flex items-start gap-3">
            <Info className="w-4.5 h-4.5 text-blue-400 shrink-0 mt-0.5" />
            <p className="text-xs text-slate-500 leading-relaxed">
              Water classification is calculated using an Isolation Forest anomaly detector and XGBoost classifier. Ensure TDS calibration occurs every 30 days.
            </p>
          </div>
        </div>
      </div>

      {/* ── Live Sensors Parameters Grid ────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* pH Card */}
        <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/30 backdrop-blur-md flex flex-col justify-between space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                <Activity className="w-4 h-4" />
              </div>
              <span className="text-sm font-semibold text-slate-400">pH Level</span>
            </div>
            <span className="text-xs text-slate-500">Bound: 6.5 - 8.5</span>
          </div>
          <div>
            <div className="flex items-baseline gap-1">
              <span className={`text-3xl font-extrabold ${phZone(latestReading?.ph || null)}`}>
                {latestReading?.ph !== undefined && latestReading.ph !== null ? latestReading.ph.toFixed(2) : '—'}
              </span>
              <span className="text-xs text-slate-500">pH</span>
            </div>
            {/* progress bar */}
            <div className="w-full bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
              <div
                className="bg-emerald-400 h-full rounded-full transition-all duration-1000"
                style={{ width: `${latestReading?.ph ? (latestReading.ph / 14) * 100 : 0}%` }}
              />
            </div>
          </div>
        </div>

        {/* TDS Card */}
        <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/30 backdrop-blur-md flex flex-col justify-between space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                <Filter className="w-4 h-4" />
              </div>
              <span className="text-sm font-semibold text-slate-400">Total Dissolved Solids</span>
            </div>
            <span className="text-xs text-slate-500">Safe: &lt; 300 ppm</span>
          </div>
          <div>
            <div className="flex items-baseline gap-1">
              <span className={`text-3xl font-extrabold ${tdsZone(latestReading?.tds || null)}`}>
                {latestReading?.tds !== undefined && latestReading.tds !== null ? Math.round(latestReading.tds) : '—'}
              </span>
              <span className="text-xs text-slate-500">ppm</span>
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
              <div
                className="bg-amber-400 h-full rounded-full transition-all duration-1000"
                style={{ width: `${latestReading?.tds ? Math.min((latestReading.tds / 1000) * 100, 100) : 0}%` }}
              />
            </div>
          </div>
        </div>

        {/* Turbidity Card */}
        <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/30 backdrop-blur-md flex flex-col justify-between space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-violet-500/10 border border-violet-500/20 flex items-center justify-center text-violet-400">
                <Droplets className="w-4 h-4" />
              </div>
              <span className="text-sm font-semibold text-slate-400">Turbidity</span>
            </div>
            <span className="text-xs text-slate-500">Safe: &lt; 5 NTU</span>
          </div>
          <div>
            <div className="flex items-baseline gap-1">
              <span className={`text-3xl font-extrabold ${turbidityZone(latestReading?.turbidity || null)}`}>
                {latestReading?.turbidity !== undefined && latestReading.turbidity !== null ? latestReading.turbidity.toFixed(2) : '—'}
              </span>
              <span className="text-xs text-slate-500">NTU</span>
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
              <div
                className="bg-violet-400 h-full rounded-full transition-all duration-1000"
                style={{ width: `${latestReading?.turbidity ? Math.min((latestReading.turbidity / 20) * 100, 100) : 0}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* ── Chart & Trends Section ──────────────────────────────── */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/30 p-6 space-y-6 backdrop-blur-md">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-4">
          <div className="flex items-center gap-3">
            <TrendingUp className="w-5 h-5 text-blue-400" />
            <h3 className="font-bold text-slate-200 text-base">Telemetry Historical Trends</h3>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {/* Chart Parameter Tabs */}
            <div className="flex rounded-lg bg-slate-950 p-1 border border-slate-800 text-xs">
              {(['wqi', 'ph', 'tds', 'turbidity'] as const).map((param) => (
                <button
                  key={param}
                  onClick={() => setActiveTab(param)}
                  className={`px-3 py-1.5 rounded-md font-semibold transition ${
                    activeTab === param ? 'bg-slate-800 text-slate-100' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {param.toUpperCase()}
                </button>
              ))}
            </div>

            {/* Time-Range selector */}
            <div className="flex rounded-lg bg-slate-950 p-1 border border-slate-800 text-xs">
              {(['24h', '7d', '30d'] as const).map((r) => (
                <button
                  key={r}
                  onClick={() => handleRangeChange(r)}
                  className={`px-3 py-1.5 rounded-md font-semibold transition ${
                    range === r ? 'bg-blue-600 text-white' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  {r.toUpperCase()}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Recharts Render */}
        <div className="h-80 w-full relative">
          {historyLoading && (
            <div className="absolute inset-0 bg-slate-950/40 backdrop-blur-[1px] flex items-center justify-center z-10">
              <RefreshCw className="w-6 h-6 text-blue-500 animate-spin" />
            </div>
          )}

          {historyData.length === 0 ? (
            <div className="h-full flex items-center justify-center border border-dashed border-slate-800 rounded-xl bg-slate-950/20">
              <p className="text-slate-500 text-sm">No historical readings detected in the selected bucket.</p>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={historyData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorWqi" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#22d3ee" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorPh" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#34d399" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#34d399" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorTds" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#fbbf24" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#fbbf24" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorTurb" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#a78bfa" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#a78bfa" stopOpacity={0} />
                  </linearGradient>
                </defs>

                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" opacity={0.4} />
                <XAxis
                  dataKey="bucket"
                  tickFormatter={formatXAxis}
                  stroke="#64748b"
                  fontSize={10}
                  tickLine={false}
                  dy={10}
                />
                <YAxis stroke="#64748b" fontSize={10} tickLine={false} dx={-5} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#0f172a', borderColor: '#1e293b', borderRadius: '12px' }}
                  labelClassName="text-slate-400 font-bold text-xs"
                  itemStyle={{ fontSize: '12px', fontWeight: 'bold' }}
                  labelFormatter={(label) => new Date(label).toLocaleString()}
                />
                <Legend verticalAlign="top" height={36} iconType="circle" />
                <Area
                  type="monotone"
                  dataKey={chartTheme[activeTab].key}
                  name={chartTheme[activeTab].label}
                  stroke={chartTheme[activeTab].stroke}
                  fillOpacity={1}
                  fill={chartTheme[activeTab].fill}
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  )
}
