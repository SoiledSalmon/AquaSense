"use client"

import React, { useEffect, useState, useRef } from 'react'
import {
  Activity,
  Users,
  Shield,
  ShieldAlert,
  Trash2,
  AlertTriangle,
  CheckCircle2,
  Droplets,
  Filter,
  TrendingUp,
  Clock,
  RefreshCw,
  Info,
  Bell,
  Check,
  BrainCircuit,
  Database,
  Search,
  ChevronLeft,
  ChevronRight,
  AlertOctagon,
  ArrowUpDown
} from 'lucide-react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from 'recharts'

import {
  getAdminStats,
  getAdminUsers,
  updateUserRole,
  deleteUser,
  getAdminReadings,
  getAdminAlerts,
  getAdminML
} from '../../lib/api/admin'

interface User {
  id: string
  email: string
  full_name?: string
  role?: string
}

export default function AdminDashboard({ user }: { user: User }) {
  const [activeTab, setActiveTab] = useState<'overview' | 'users' | 'readings' | 'alerts' | 'ml' | 'status'>('overview')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // --- Overview State ---
  const [stats, setStats] = useState<any>(null)
  const [statsLoading, setStatsLoading] = useState(false)

  // --- Users State ---
  const [usersList, setUsersList] = useState<any[]>([])
  const [usersCount, setUsersCount] = useState(0)
  const [usersPage, setUsersPage] = useState(1)
  const [usersSearch, setUsersSearch] = useState('')
  const [usersRoleFilter, setUsersRoleFilter] = useState('all')
  const [usersSortBy, setUsersSortBy] = useState('created_at')
  const [usersSortOrder, setUsersSortOrder] = useState('desc')
  const [usersLoading, setUsersLoading] = useState(false)
  const [updatingUserId, setUpdatingUserId] = useState<string | null>(null)
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null)

  // --- Readings State ---
  const [readingsList, setReadingsList] = useState<any[]>([])
  const [readingsCount, setReadingsCount] = useState(0)
  const [readingsPage, setReadingsPage] = useState(1)
  const [readingsLabelFilter, setReadingsLabelFilter] = useState('all')
  const [readingsUserFilter, setReadingsUserFilter] = useState('')
  const [readingsLoading, setReadingsLoading] = useState(false)

  // --- Alerts State ---
  const [alertsList, setAlertsList] = useState<any[]>([])
  const [alertsCount, setAlertsCount] = useState(0)
  const [alertsPage, setAlertsPage] = useState(1)
  const [alertsSeverityFilter, setAlertsSeverityFilter] = useState('all')
  const [alertsAckFilter, setAlertsAckFilter] = useState<string>('all')
  const [alertsLoading, setAlertsLoading] = useState(false)

  // --- ML Predictions State ---
  const [mlList, setMlList] = useState<any[]>([])
  const [mlCount, setMlCount] = useState(0)
  const [mlPage, setMlPage] = useState(1)
  const [mlRiskFilter, setMlRiskFilter] = useState('all')
  const [mlAnomalyFilter, setMlAnomalyFilter] = useState<string>('all')
  const [mlLoading, setMlLoading] = useState(false)

  const itemsPerPage = 10

  // Fetch stats (Overview tab)
  const fetchStats = async () => {
    try {
      setStatsLoading(true)
      const res = await getAdminStats()
      if (res) {
        setStats(res)
      }
    } catch (err: any) {
      console.error(err)
      setError(err.message || 'Failed to load system statistics')
    } finally {
      setStatsLoading(false)
      setLoading(false)
    }
  }

  // Fetch Users
  const fetchUsers = async () => {
    try {
      setUsersLoading(true)
      const res = await getAdminUsers({
        search: usersSearch || undefined,
        role: usersRoleFilter !== 'all' ? usersRoleFilter : undefined,
        sortBy: usersSortBy,
        order: usersSortOrder,
        page: usersPage,
        limit: itemsPerPage
      })
      if (res) {
        setUsersList(res.users)
        setUsersCount(res.total_count)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load users list')
    } finally {
      setUsersLoading(false)
    }
  }

  // Fetch Readings
  const fetchReadings = async () => {
    try {
      setReadingsLoading(true)
      const res = await getAdminReadings({
        userId: readingsUserFilter || undefined,
        label: readingsLabelFilter !== 'all' ? readingsLabelFilter : undefined,
        page: readingsPage,
        limit: itemsPerPage
      })
      if (res) {
        setReadingsList(res.readings)
        setReadingsCount(res.total_count)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load telemetry readings')
    } finally {
      setReadingsLoading(false)
    }
  }

  // Fetch Alerts
  const fetchAlerts = async () => {
    try {
      setAlertsLoading(true)
      const res = await getAdminAlerts({
        severity: alertsSeverityFilter !== 'all' ? alertsSeverityFilter : undefined,
        isAcknowledged: alertsAckFilter === 'ack' ? true : alertsAckFilter === 'unack' ? false : undefined,
        page: alertsPage,
        limit: itemsPerPage
      })
      if (res) {
        setAlertsList(res.alerts)
        setAlertsCount(res.total_count)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load alerts')
    } finally {
      setAlertsLoading(false)
    }
  }

  // Fetch ML predictions
  const fetchML = async () => {
    try {
      setMlLoading(true)
      const res = await getAdminML({
        riskLevel: mlRiskFilter !== 'all' ? mlRiskFilter : undefined,
        isAnomaly: mlAnomalyFilter === 'anomaly' ? true : mlAnomalyFilter === 'normal' ? false : undefined,
        page: mlPage,
        limit: itemsPerPage
      })
      if (res) {
        setMlList(res.predictions)
        setMlCount(res.total_count)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load machine learning predictions')
    } finally {
      setMlLoading(false)
    }
  }

  // Trigger loading data on tab change or filter/page change
  useEffect(() => {
    if (activeTab === 'overview' || activeTab === 'status') {
      fetchStats()
    }
  }, [activeTab])

  useEffect(() => {
    if (activeTab === 'users') {
      fetchUsers()
    }
  }, [activeTab, usersPage, usersRoleFilter, usersSortBy, usersSortOrder])

  // Simple debounce for users search
  useEffect(() => {
    if (activeTab === 'users') {
      const timer = setTimeout(() => {
        setUsersPage(1)
        fetchUsers()
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [usersSearch])

  useEffect(() => {
    if (activeTab === 'readings') {
      fetchReadings()
    }
  }, [activeTab, readingsPage, readingsLabelFilter, readingsUserFilter])

  useEffect(() => {
    if (activeTab === 'alerts') {
      fetchAlerts()
    }
  }, [activeTab, alertsPage, alertsSeverityFilter, alertsAckFilter])

  useEffect(() => {
    if (activeTab === 'ml') {
      fetchML()
    }
  }, [activeTab, mlPage, mlRiskFilter, mlAnomalyFilter])

  // --- Actions ---
  const handleToggleRole = async (targetUser: any) => {
    const newRole = targetUser.role === 'admin' ? 'user' : 'admin'
    try {
      setUpdatingUserId(targetUser.id)
      await updateUserRole(targetUser.id, newRole)
      fetchUsers()
    } catch (err: any) {
      alert(err.message || 'Failed to update user role')
    } finally {
      setUpdatingUserId(null)
    }
  }

  const handleDeleteUserAccount = async (userId: string) => {
    try {
      setUpdatingUserId(userId)
      await deleteUser(userId)
      setConfirmDeleteId(null)
      fetchUsers()
    } catch (err: any) {
      alert(err.message || 'Failed to delete user account')
    } finally {
      setUpdatingUserId(null)
    }
  }

  const getWqiColor = (score: number) => {
    if (score >= 95) return 'text-emerald-400'
    if (score >= 80) return 'text-blue-400'
    if (score >= 65) return 'text-yellow-400'
    if (score >= 45) return 'text-orange-400'
    return 'text-rose-500'
  }

  const getWqiBg = (score: number) => {
    if (score >= 95) return 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
    if (score >= 80) return 'bg-blue-500/10 border-blue-500/20 text-blue-400'
    if (score >= 65) return 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400'
    if (score >= 45) return 'bg-orange-500/10 border-orange-500/20 text-orange-400'
    return 'bg-rose-500/10 border-rose-500/20 text-rose-400'
  }

  // --- Prepare SHAP graph data ---
  const getShapChartData = () => {
    if (!mlList || mlList.length === 0) return []
    // Get averages of shap values in mlList
    let phSum = 0, tdsSum = 0, turbSum = 0, count = 0
    mlList.forEach(item => {
      if (item.shap_ph !== null && item.shap_tds !== null && item.shap_turbidity !== null) {
        phSum += Math.abs(item.shap_ph)
        tdsSum += Math.abs(item.shap_tds)
        turbSum += Math.abs(item.shap_turbidity)
        count++
      }
    })

    if (count === 0) return []

    return [
      { name: 'pH Contribution', value: Number((phSum / count).toFixed(4)), fill: '#3b82f6' },
      { name: 'TDS Contribution', value: Number((tdsSum / count).toFixed(4)), fill: '#06b6d4' },
      { name: 'Turbidity Contribution', value: Number((turbSum / count).toFixed(4)), fill: '#a855f7' }
    ]
  }

  if (loading && !stats) {
    return (
      <div className="flex h-96 items-center justify-center">
        <RefreshCw className="h-10 w-10 animate-spin text-blue-500" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <div className="flex items-center gap-2">
            <Shield className="h-6 w-6 text-purple-400" />
            <h1 className="text-2xl font-extrabold tracking-tight text-slate-100 md:text-3xl">
              System Administration
            </h1>
          </div>
          <p className="text-slate-400 text-sm mt-1">
            Global monitoring panel for user profiles, real-time channels, alert queues, and ML performance.
          </p>
        </div>

        <button
          onClick={() => {
            fetchStats()
            if (activeTab === 'users') fetchUsers()
            if (activeTab === 'readings') fetchReadings()
            if (activeTab === 'alerts') fetchAlerts()
            if (activeTab === 'ml') fetchML()
          }}
          className="flex items-center justify-center gap-2 px-4 py-2 text-sm bg-slate-900 border border-slate-800 hover:border-slate-700 text-slate-300 rounded-lg hover:text-white transition-all duration-200"
        >
          <RefreshCw className={`h-4 w-4 ${statsLoading ? 'animate-spin' : ''}`} />
          Reload Data
        </button>
      </div>

      {error && (
        <div className="bg-rose-950/20 border border-rose-900/30 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-rose-400 mt-0.5" />
          <div className="flex-1">
            <h4 className="font-semibold text-rose-300 text-sm">System Error</h4>
            <p className="text-rose-400 text-xs mt-1">{error}</p>
          </div>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-300 text-xs">Dismiss</button>
        </div>
      )}

      {/* Tabs list */}
      <div className="flex flex-wrap border-b border-slate-800">
        {[
          { id: 'overview', name: 'Overview', icon: Activity },
          { id: 'users', name: 'User Management', icon: Users },
          { id: 'readings', name: 'Sensor Readings', icon: Droplets },
          { id: 'alerts', name: 'System Alerts', icon: ShieldAlert },
          { id: 'ml', name: 'Machine Learning', icon: BrainCircuit },
          { id: 'status', name: 'System Health', icon: Database }
        ].map((t: any) => {
          const Icon = t.icon
          const active = activeTab === t.id
          return (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`flex items-center gap-2 px-5 py-3 border-b-2 font-semibold text-sm transition-all duration-250 ${
                active
                  ? 'border-purple-500 text-purple-400 bg-purple-500/5'
                  : 'border-transparent text-slate-400 hover:text-slate-200 hover:bg-slate-900/30'
              }`}
            >
              <Icon className={`h-4 w-4 ${active ? 'text-purple-400' : 'text-slate-400'}`} />
              {t.name}
            </button>
          )
        })}
      </div>

      {/* TAB CONTENT: Overview */}
      {activeTab === 'overview' && stats && (
        <div className="space-y-6">
          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { title: 'Active Users', value: stats.active_users_count, subtitle: 'Configured channel IDs', icon: Users, color: 'text-blue-400' },
              { title: 'Total Telemetry Items', value: stats.total_readings_count.toLocaleString(), subtitle: 'Ingested over MQTT', icon: Droplets, color: 'text-cyan-400' },
              { title: 'Unsafe Incidents', value: stats.unsafe_events_count, subtitle: 'WQI safety events logged', icon: AlertTriangle, color: 'text-rose-500' },
              { title: 'Average WQI', value: stats.average_wqi, subtitle: 'Global water quality average', icon: TrendingUp, color: getWqiColor(stats.average_wqi) }
            ].map((card, idx) => {
              const Icon = card.icon
              return (
                <div key={idx} className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 backdrop-blur-md hover:border-slate-700/80 transition-all duration-300">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="text-slate-500 text-xs font-semibold uppercase tracking-wider">{card.title}</p>
                      <h3 className="text-3xl font-extrabold text-slate-100 mt-2">{card.value}</h3>
                    </div>
                    <div className={`p-2.5 rounded-lg bg-slate-950 border border-slate-800 ${card.color}`}>
                      <Icon className="h-5 w-5" />
                    </div>
                  </div>
                  <p className="text-slate-400 text-xs mt-3 flex items-center gap-1">
                    <Clock className="h-3 w-3 text-slate-500" />
                    {card.subtitle}
                  </p>
                </div>
              )
            })}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Trends Chart */}
            <div className="lg:col-span-2 bg-slate-900/40 border border-slate-800 rounded-xl p-5 md:p-6 backdrop-blur-md">
              <h3 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
                <TrendingUp className="h-5 w-5 text-purple-400" />
                Global Water Quality Index (Trends)
              </h3>
              <div className="h-80 w-full mt-4">
                {stats.trends && stats.trends.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={stats.trends}>
                      <defs>
                        <linearGradient id="colorWqi" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#a855f7" stopOpacity={0.2}/>
                          <stop offset="95%" stopColor="#a855f7" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="date" stroke="#64748b" fontSize={11} tickLine={false} />
                      <YAxis domain={[0, 100]} stroke="#64748b" fontSize={11} tickLine={false} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                        labelStyle={{ color: '#94a3b8', fontWeight: 'bold' }}
                      />
                      <Area type="monotone" dataKey="avg_wqi" stroke="#a855f7" strokeWidth={2} fillOpacity={1} fill="url(#colorWqi)" name="Avg WQI" />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex h-full items-center justify-center text-slate-500 text-sm">
                    No historical trend data found
                  </div>
                )}
              </div>
            </div>

            {/* Quick Status and Frequency info */}
            <div className="space-y-6">
              {/* System status */}
              <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 backdrop-blur-md">
                <h3 className="text-base font-bold text-slate-100 mb-4 flex items-center gap-2">
                  <Database className="h-4.5 w-4.5 text-blue-400" />
                  System Component Status
                </h3>
                <div className="space-y-4">
                  <div className="flex justify-between items-center bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                    <span className="text-sm font-medium text-slate-300">Database Connection</span>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${
                      stats.system_status?.database === 'healthy'
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                        : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                    }`}>
                      {stats.system_status?.database?.toUpperCase() || 'UNKNOWN'}
                    </span>
                  </div>

                  <div className="flex justify-between items-center bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                    <span className="text-sm font-medium text-slate-300">MQTT subscriber</span>
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${
                      stats.system_status?.mqtt_subscriber === 'connected'
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                        : stats.system_status?.mqtt_subscriber === 'starting'
                        ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400'
                        : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                    }`}>
                      {stats.system_status?.mqtt_subscriber?.toUpperCase() || 'UNKNOWN'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Alert frequencies */}
              <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 backdrop-blur-md">
                <h3 className="text-base font-bold text-slate-100 mb-4 flex items-center gap-2">
                  <Bell className="h-4.5 w-4.5 text-amber-400" />
                  Alert Frequency
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-slate-950/60 p-4 rounded-lg border border-slate-800 text-center">
                    <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Last 24 Hours</p>
                    <p className="text-2xl font-extrabold text-slate-200 mt-2">{stats.alert_frequency?.last_24h}</p>
                  </div>
                  <div className="bg-slate-950/60 p-4 rounded-lg border border-slate-800 text-center">
                    <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Last 7 Days</p>
                    <p className="text-2xl font-extrabold text-slate-200 mt-2">{stats.alert_frequency?.last_7d}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB CONTENT: User Management */}
      {activeTab === 'users' && (
        <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 md:p-6 backdrop-blur-md space-y-6">
          {/* Filters & search */}
          <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
            <div className="relative w-full md:max-w-md">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
              <input
                type="text"
                placeholder="Search users by name or email..."
                value={usersSearch}
                onChange={(e) => setUsersSearch(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-10 pr-4 py-2 text-sm text-slate-200 focus:outline-none focus:border-slate-700 placeholder-slate-500"
              />
            </div>

            <div className="flex gap-4 w-full md:w-auto">
              <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 w-full md:w-auto">
                <Filter className="h-4 w-4 text-slate-500" />
                <select
                  value={usersRoleFilter}
                  onChange={(e) => {
                    setUsersPage(1)
                    setUsersRoleFilter(e.target.value)
                  }}
                  className="bg-transparent border-0 text-sm text-slate-300 focus:outline-none w-full md:w-auto cursor-pointer"
                >
                  <option value="all" className="bg-slate-950 text-slate-300">All Roles</option>
                  <option value="user" className="bg-slate-950 text-slate-300">User Only</option>
                  <option value="admin" className="bg-slate-950 text-slate-300">Admin Only</option>
                </select>
              </div>
            </div>
          </div>

          {/* User deletion confirmation modal overlay */}
          {confirmDeleteId && (
            <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
              <div className="bg-slate-900 border border-slate-800 max-w-md w-full rounded-2xl p-6 space-y-4">
                <div className="flex gap-3 text-rose-500">
                  <AlertOctagon className="h-6 w-6 mt-0.5" />
                  <div>
                    <h3 className="text-lg font-bold text-slate-100">Permanently Delete User?</h3>
                    <p className="text-sm text-slate-400 mt-2">
                      This action will immediately delete the user from Supabase authentication databases. All telemetry records, warnings, and anomaly history will be deleted.
                    </p>
                  </div>
                </div>
                <div className="flex justify-end gap-3 pt-3">
                  <button
                    onClick={() => setConfirmDeleteId(null)}
                    className="px-4 py-2 border border-slate-800 bg-slate-950 text-slate-400 text-sm font-semibold rounded-lg hover:text-white transition-all duration-200"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() => handleDeleteUserAccount(confirmDeleteId)}
                    disabled={updatingUserId !== null}
                    className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white text-sm font-semibold rounded-lg transition-all duration-200 flex items-center gap-2"
                  >
                    {updatingUserId !== null && <RefreshCw className="h-4.5 w-4.5 animate-spin" />}
                    Delete User
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Table */}
          <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950/20">
            {usersLoading ? (
              <div className="flex h-40 items-center justify-center">
                <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
              </div>
            ) : (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-950/60 border-b border-slate-800">
                    <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">User Details</th>
                    <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">Role</th>
                    <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">ThingSpeak Channel</th>
                    <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">Phone</th>
                    <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">Registered</th>
                    <th className="p-4 text-xs text-right uppercase font-bold text-slate-400 tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {usersList.length > 0 ? (
                    usersList.map((usr) => (
                      <tr key={usr.id} className="hover:bg-slate-900/20 transition-all duration-200">
                        <td className="p-4">
                          <p className="text-sm font-semibold text-slate-200">{usr.full_name || 'No Name'}</p>
                          <p className="text-xs text-slate-500 mt-0.5">{usr.email}</p>
                        </td>
                        <td className="p-4">
                          <span className={`text-[11px] font-bold uppercase px-2 py-0.5 rounded border ${
                            usr.role === 'admin'
                              ? 'bg-purple-500/10 border-purple-500/20 text-purple-400'
                              : 'bg-slate-800 border-slate-700 text-slate-300'
                          }`}>
                            {usr.role}
                          </span>
                        </td>
                        <td className="p-4 text-sm font-mono text-slate-300">
                          {usr.channel_id || <span className="text-slate-600">Not Configured</span>}
                        </td>
                        <td className="p-4 text-sm text-slate-300">{usr.phone || '-'}</td>
                        <td className="p-4 text-xs text-slate-400">
                          {new Date(usr.created_at).toLocaleDateString()}
                        </td>
                        <td className="p-4 text-right">
                          <div className="flex gap-2 justify-end">
                            <button
                              onClick={() => handleToggleRole(usr)}
                              disabled={updatingUserId !== null || usr.id === user.id}
                              className="px-2.5 py-1 text-xs bg-slate-900 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 rounded text-slate-300 disabled:opacity-50"
                              title={usr.role === 'admin' ? 'Demote to User' : 'Promote to Admin'}
                            >
                              {usr.role === 'admin' ? 'Demote' : 'Promote'}
                            </button>
                            <button
                              onClick={() => setConfirmDeleteId(usr.id)}
                              disabled={usr.id === user.id}
                              className="p-1 text-rose-500 hover:text-rose-400 bg-rose-500/5 hover:bg-rose-500/10 border border-rose-500/10 rounded disabled:opacity-50"
                              title="Delete Account"
                            >
                              <Trash2 className="h-4.5 w-4.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="p-6 text-center text-slate-500 text-sm">
                        No user profiles found matching filters
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>

          {/* Pagination */}
          {usersCount > itemsPerPage && (
            <div className="flex items-center justify-between border-t border-slate-800 pt-4">
              <span className="text-xs text-slate-500">
                Showing {(usersPage - 1) * itemsPerPage + 1} to {Math.min(usersPage * itemsPerPage, usersCount)} of {usersCount} users
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setUsersPage(p => Math.max(p - 1, 1))}
                  disabled={usersPage === 1}
                  className="p-1.5 border border-slate-800 bg-slate-950 text-slate-400 rounded-lg hover:text-white disabled:opacity-50 transition-all duration-200"
                >
                  <ChevronLeft className="h-4.5 w-4.5" />
                </button>
                <button
                  onClick={() => setUsersPage(p => Math.min(p + 1, Math.ceil(usersCount / itemsPerPage)))}
                  disabled={usersPage === Math.ceil(usersCount / itemsPerPage)}
                  className="p-1.5 border border-slate-800 bg-slate-950 text-slate-400 rounded-lg hover:text-white disabled:opacity-50 transition-all duration-200"
                >
                  <ChevronRight className="h-4.5 w-4.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: Sensor Readings */}
      {activeTab === 'readings' && (
        <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 md:p-6 backdrop-blur-md space-y-6">
          <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Droplets className="h-5 w-5 text-blue-400" />
              Global Telemetry Log
            </h3>

            <div className="flex flex-wrap gap-3 w-full md:w-auto">
              <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5">
                <Filter className="h-4 w-4 text-slate-500" />
                <select
                  value={readingsLabelFilter}
                  onChange={(e) => {
                    setReadingsPage(1)
                    setReadingsLabelFilter(e.target.value)
                  }}
                  className="bg-transparent border-0 text-sm text-slate-300 focus:outline-none cursor-pointer"
                >
                  <option value="all" className="bg-slate-950 text-slate-300">All Levels</option>
                  <option value="safe" className="bg-slate-950 text-slate-300">Safe Only</option>
                  <option value="borderline" className="bg-slate-950 text-slate-300">Borderline Only</option>
                  <option value="unsafe" className="bg-slate-950 text-slate-300">Unsafe Only</option>
                </select>
              </div>

              <input
                type="text"
                placeholder="Filter by User UUID..."
                value={readingsUserFilter}
                onChange={(e) => {
                  setReadingsPage(1)
                  setReadingsUserFilter(e.target.value)
                }}
                className="bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-sm text-slate-300 focus:outline-none placeholder-slate-600 w-full md:w-48"
              />
            </div>
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950/20">
            {readingsLoading ? (
              <div className="flex h-40 items-center justify-center">
                <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
              </div>
            ) : (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-950/60 border-b border-slate-800">
                    <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">Timestamp</th>
                    <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">User Account</th>
                    <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">pH</th>
                    <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">TDS</th>
                    <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">Turbidity</th>
                    <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">WQI Score</th>
                    <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">Safety Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {readingsList.length > 0 ? (
                    readingsList.map((r) => (
                      <tr key={r.id} className="hover:bg-slate-900/10 transition-all duration-200">
                        <td className="p-4 text-sm font-mono text-slate-300">
                          {new Date(r.timestamp).toLocaleString()}
                        </td>
                        <td className="p-4">
                          <p className="text-sm font-semibold text-slate-200">{r.user_email || 'No email'}</p>
                          <p className="text-[10px] font-mono text-slate-500">{r.user_id}</p>
                        </td>
                        <td className="p-4 text-sm text-slate-200 font-mono">{r.ph !== null ? Number(r.ph).toFixed(2) : '-'}</td>
                        <td className="p-4 text-sm text-slate-200 font-mono">{r.tds !== null ? `${Number(r.tds).toFixed(0)} ppm` : '-'}</td>
                        <td className="p-4 text-sm text-slate-200 font-mono">{r.turbidity !== null ? `${Number(r.turbidity).toFixed(1)} NTU` : '-'}</td>
                        <td className={`p-4 text-sm font-bold font-mono ${getWqiColor(r.wqi_score)}`}>
                          {r.wqi_score !== null ? Number(r.wqi_score).toFixed(1) : '-'}
                        </td>
                        <td className="p-4">
                          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${getWqiBg(r.wqi_score)}`}>
                            {r.label || 'unknown'}
                          </span>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={7} className="p-6 text-center text-slate-500 text-sm">
                        No telemetry readings logged in this interval
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>

          {/* Pagination */}
          {readingsCount > itemsPerPage && (
            <div className="flex items-center justify-between border-t border-slate-800 pt-4">
              <span className="text-xs text-slate-500">
                Showing {(readingsPage - 1) * itemsPerPage + 1} to {Math.min(readingsPage * itemsPerPage, readingsCount)} of {readingsCount} records
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setReadingsPage(p => Math.max(p - 1, 1))}
                  disabled={readingsPage === 1}
                  className="p-1.5 border border-slate-800 bg-slate-950 text-slate-400 rounded-lg hover:text-white disabled:opacity-50 transition-all duration-200"
                >
                  <ChevronLeft className="h-4.5 w-4.5" />
                </button>
                <button
                  onClick={() => setReadingsPage(p => Math.min(p + 1, Math.ceil(readingsCount / itemsPerPage)))}
                  disabled={readingsPage === Math.ceil(readingsCount / itemsPerPage)}
                  className="p-1.5 border border-slate-800 bg-slate-950 text-slate-400 rounded-lg hover:text-white disabled:opacity-50 transition-all duration-200"
                >
                  <ChevronRight className="h-4.5 w-4.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: System Alerts */}
      {activeTab === 'alerts' && (
        <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 md:p-6 backdrop-blur-md space-y-6">
          <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-amber-500" />
              Global Water Quality Alerts Queue
            </h3>

            <div className="flex flex-wrap gap-3 w-full md:w-auto">
              <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5">
                <Filter className="h-4 w-4 text-slate-500" />
                <select
                  value={alertsSeverityFilter}
                  onChange={(e) => {
                    setAlertsPage(1)
                    setAlertsSeverityFilter(e.target.value)
                  }}
                  className="bg-transparent border-0 text-sm text-slate-300 focus:outline-none cursor-pointer"
                >
                  <option value="all" className="bg-slate-950 text-slate-300">All Severities</option>
                  <option value="info" className="bg-slate-950 text-slate-300">Info Only</option>
                  <option value="warning" className="bg-slate-950 text-slate-300">Warning Only</option>
                  <option value="critical" className="bg-slate-950 text-slate-300">Critical Only</option>
                </select>
              </div>

              <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5">
                <select
                  value={alertsAckFilter}
                  onChange={(e) => {
                    setAlertsPage(1)
                    setAlertsAckFilter(e.target.value)
                  }}
                  className="bg-transparent border-0 text-sm text-slate-300 focus:outline-none cursor-pointer"
                >
                  <option value="all" className="bg-slate-950 text-slate-300">All States</option>
                  <option value="unack" className="bg-slate-950 text-slate-300">Unacknowledged</option>
                  <option value="ack" className="bg-slate-950 text-slate-300">Acknowledged</option>
                </select>
              </div>
            </div>
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950/20">
            {alertsLoading ? (
              <div className="flex h-40 items-center justify-center">
                <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
              </div>
            ) : (
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-950/60 border-b border-slate-800">
                    <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">Timestamp</th>
                    <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">User</th>
                    <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">Message</th>
                    <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">Severity</th>
                    <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">Category</th>
                    <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {alertsList.length > 0 ? (
                    alertsList.map((a) => (
                      <tr key={a.id} className="hover:bg-slate-900/10 transition-all duration-200">
                        <td className="p-4 text-sm font-mono text-slate-300">
                          {new Date(a.timestamp).toLocaleString()}
                        </td>
                        <td className="p-4 text-sm font-semibold text-slate-200">
                          {a.user_email || 'No email'}
                        </td>
                        <td className="p-4 text-sm text-slate-300 max-w-xs md:max-w-md">
                          <div>
                            <p className="font-medium text-slate-200">{a.message}</p>
                            {a.recommendation && (
                              <p className="text-xs text-amber-500 mt-1 italic">Recommendation: {a.recommendation}</p>
                            )}
                          </div>
                        </td>
                        <td className="p-4">
                          <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${
                            a.severity === 'critical'
                              ? 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                              : a.severity === 'warning'
                              ? 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                              : 'bg-blue-500/10 border-blue-500/20 text-blue-400'
                          }`}>
                            {a.severity}
                          </span>
                        </td>
                        <td className="p-4 text-sm text-slate-300 font-mono">{a.category}</td>
                        <td className="p-4 space-y-1">
                          <div className="flex gap-2">
                            <span className={`text-[10px] font-bold uppercase px-1.5 py-0.25 rounded border ${
                              a.is_acknowledged
                                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                                : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                            }`}>
                              {a.is_acknowledged ? 'ACK' : 'UNACK'}
                            </span>
                            <span className={`text-[10px] font-bold uppercase px-1.5 py-0.25 rounded border ${
                              a.is_resolved
                                ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                                : 'bg-amber-500/10 border-amber-500/20 text-amber-400'
                            }`}>
                              {a.is_resolved ? 'RESOLVED' : 'ACTIVE'}
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="p-6 text-center text-slate-500 text-sm">
                        No alerts logged matching the filter parameters
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            )}
          </div>

          {/* Pagination */}
          {alertsCount > itemsPerPage && (
            <div className="flex items-center justify-between border-t border-slate-800 pt-4">
              <span className="text-xs text-slate-500">
                Showing {(alertsPage - 1) * itemsPerPage + 1} to {Math.min(alertsPage * itemsPerPage, alertsCount)} of {alertsCount} alerts
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setAlertsPage(p => Math.max(p - 1, 1))}
                  disabled={alertsPage === 1}
                  className="p-1.5 border border-slate-800 bg-slate-950 text-slate-400 rounded-lg hover:text-white disabled:opacity-50 transition-all duration-200"
                >
                  <ChevronLeft className="h-4.5 w-4.5" />
                </button>
                <button
                  onClick={() => setAlertsPage(p => Math.min(p + 1, Math.ceil(alertsCount / itemsPerPage)))}
                  disabled={alertsPage === Math.ceil(alertsCount / itemsPerPage)}
                  className="p-1.5 border border-slate-800 bg-slate-950 text-slate-400 rounded-lg hover:text-white disabled:opacity-50 transition-all duration-200"
                >
                  <ChevronRight className="h-4.5 w-4.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* TAB CONTENT: Machine Learning */}
      {activeTab === 'ml' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* SHAP contributions graph */}
            <div className="lg:col-span-2 bg-slate-900/40 border border-slate-800 rounded-xl p-5 md:p-6 backdrop-blur-md">
              <h3 className="text-lg font-bold text-slate-100 mb-4 flex items-center gap-2">
                <BrainCircuit className="h-5 w-5 text-purple-400" />
                Average Feature Contribution (SHAP Explainers)
              </h3>
              <p className="text-slate-400 text-xs mt-1">
                Relative importance of pH, TDS, and Turbidity values in deciding anomaly classifications for recent runs.
              </p>
              <div className="h-64 w-full mt-6">
                {mlList && mlList.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={getShapChartData()} layout="vertical" margin={{ left: 30, right: 30, top: 10, bottom: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                      <XAxis type="number" stroke="#64748b" fontSize={11} tickLine={false} />
                      <YAxis dataKey="name" type="category" stroke="#64748b" fontSize={11} tickLine={false} width={150} />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                        itemStyle={{ color: '#e2e8f0' }}
                      />
                      <Bar dataKey="value" strokeWidth={1} radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex h-full items-center justify-center text-slate-500 text-sm">
                    No ML predictions found to calculate SHAP values
                  </div>
                )}
              </div>
            </div>

            {/* Prediction distribution stats */}
            {stats && (
              <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 backdrop-blur-md flex flex-col justify-between">
                <div>
                  <h3 className="text-base font-bold text-slate-100 mb-4 flex items-center gap-2">
                    <Activity className="h-4.5 w-4.5 text-cyan-400" />
                    Classification Distribution
                  </h3>
                  <div className="space-y-3">
                    <div className="flex justify-between items-center bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                      <span className="text-sm font-medium text-slate-300">Anomalies Detected</span>
                      <span className="text-sm font-bold text-rose-400 font-mono">
                        {stats.ml_prediction_distribution?.anomaly_count}
                      </span>
                    </div>

                    <div className="flex justify-between items-center bg-slate-950/60 p-3 rounded-lg border border-slate-800">
                      <span className="text-sm font-medium text-slate-300">Normal Conditions</span>
                      <span className="text-sm font-bold text-emerald-400 font-mono">
                        {stats.ml_prediction_distribution?.normal_count}
                      </span>
                    </div>

                    <div className="border-t border-slate-800 my-2 pt-2" />

                    <div className="flex justify-between items-center bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                      <span className="text-xs font-medium text-slate-400">High Risk Scores</span>
                      <span className="text-xs font-bold text-rose-400 font-mono">
                        {stats.ml_prediction_distribution?.high_risk}
                      </span>
                    </div>

                    <div className="flex justify-between items-center bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                      <span className="text-xs font-medium text-slate-400">Medium Risk Scores</span>
                      <span className="text-xs font-bold text-yellow-400 font-mono">
                        {stats.ml_prediction_distribution?.medium_risk}
                      </span>
                    </div>

                    <div className="flex justify-between items-center bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
                      <span className="text-xs font-medium text-slate-400">Low Risk Scores</span>
                      <span className="text-xs font-bold text-emerald-400 font-mono">
                        {stats.ml_prediction_distribution?.low_risk}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="text-[11px] text-slate-500 bg-slate-950 border border-slate-800 p-2.5 rounded-lg mt-4 flex gap-1.5 items-start">
                  <Info className="h-4 w-4 text-slate-400 shrink-0 mt-0.5" />
                  <span>
                    Isolation Forest model assesses anomalies; XGBoost predicts WQI scores; SHAP generates feature attributions.
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* ML Results Logs */}
          <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 md:p-6 backdrop-blur-md space-y-6">
            <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
              <h3 className="text-base font-bold text-slate-100">
                Machine Learning Prediction History Log
              </h3>

              <div className="flex gap-3 w-full md:w-auto">
                <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5">
                  <Filter className="h-4 w-4 text-slate-500" />
                  <select
                    value={mlRiskFilter}
                    onChange={(e) => {
                      setMlPage(1)
                      setMlRiskFilter(e.target.value)
                    }}
                    className="bg-transparent border-0 text-sm text-slate-300 focus:outline-none cursor-pointer"
                  >
                    <option value="all" className="bg-slate-950 text-slate-300">All Risks</option>
                    <option value="low" className="bg-slate-950 text-slate-300">Low Risk Only</option>
                    <option value="medium" className="bg-slate-950 text-slate-300">Medium Risk Only</option>
                    <option value="high" className="bg-slate-950 text-slate-300">High Risk Only</option>
                  </select>
                </div>

                <div className="flex items-center gap-2 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5">
                  <select
                    value={mlAnomalyFilter}
                    onChange={(e) => {
                      setMlPage(1)
                      setMlAnomalyFilter(e.target.value)
                    }}
                    className="bg-transparent border-0 text-sm text-slate-300 focus:outline-none cursor-pointer"
                  >
                    <option value="all" className="bg-slate-950 text-slate-300">All Conditions</option>
                    <option value="anomaly" className="bg-slate-950 text-slate-300">Anomalies</option>
                    <option value="normal" className="bg-slate-950 text-slate-300">Normal</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="overflow-x-auto rounded-lg border border-slate-800 bg-slate-950/20">
              {mlLoading ? (
                <div className="flex h-40 items-center justify-center">
                  <RefreshCw className="h-8 w-8 animate-spin text-blue-500" />
                </div>
              ) : (
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="bg-slate-950/60 border-b border-slate-800">
                      <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">Timestamp</th>
                      <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">User</th>
                      <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">Smoothed (pH/TDS/Turb)</th>
                      <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">Anomaly Score</th>
                      <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">Risk Level</th>
                      <th className="p-4 text-xs uppercase font-bold text-slate-400 tracking-wider">SHAP values</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {mlList.length > 0 ? (
                      mlList.map((p) => (
                        <tr key={p.id} className="hover:bg-slate-900/10 transition-all duration-200">
                          <td className="p-4 text-sm font-mono text-slate-300">
                            {new Date(p.timestamp).toLocaleString()}
                          </td>
                          <td className="p-4 text-sm">
                            <p className="font-semibold text-slate-200">{p.user_email || 'No email'}</p>
                          </td>
                          <td className="p-4 text-xs font-mono text-slate-300">
                            pH: {p.ph_smoothed !== null ? Number(p.ph_smoothed).toFixed(2) : '-'} |
                            TDS: {p.tds_smoothed !== null ? `${Number(p.tds_smoothed).toFixed(0)} ppm` : '-'} |
                            Turb: {p.turb_smoothed !== null ? `${Number(p.turb_smoothed).toFixed(1)} NTU` : '-'}
                          </td>
                          <td className="p-4 text-sm font-mono text-slate-300">
                            <span className={p.is_anomaly ? 'text-rose-400 font-bold' : 'text-slate-300'}>
                              {p.anomaly_score !== null ? Number(p.anomaly_score).toFixed(4) : '-'}
                            </span>
                            {p.is_anomaly && (
                              <span className="text-[9px] font-bold uppercase ml-2 px-1 py-0.2 bg-rose-500/10 border border-rose-500/20 text-rose-400 rounded">
                                ANOMALY
                              </span>
                            )}
                          </td>
                          <td className="p-4">
                            <span className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded border ${
                              p.risk_level === 'high'
                                ? 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                                : p.risk_level === 'medium'
                                ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400'
                                : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                            }`}>
                              {p.risk_level || 'low'}
                            </span>
                          </td>
                          <td className="p-4 text-xs font-mono text-slate-400">
                            pH: {p.shap_ph !== null ? Number(p.shap_ph).toFixed(4) : '-'} |
                            TDS: {p.shap_tds !== null ? Number(p.shap_tds).toFixed(4) : '-'} |
                            Turb: {p.shap_turbidity !== null ? Number(p.shap_turbidity).toFixed(4) : '-'}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={6} className="p-6 text-center text-slate-500 text-sm">
                          No ML prediction records found matching the filter parameters
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              )}
            </div>

            {/* Pagination */}
            {mlCount > itemsPerPage && (
              <div className="flex items-center justify-between border-t border-slate-800 pt-4">
                <span className="text-xs text-slate-500">
                  Showing {(mlPage - 1) * itemsPerPage + 1} to {Math.min(mlPage * itemsPerPage, mlCount)} of {mlCount} predictions
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setMlPage(p => Math.max(p - 1, 1))}
                    disabled={mlPage === 1}
                    className="p-1.5 border border-slate-800 bg-slate-950 text-slate-400 rounded-lg hover:text-white disabled:opacity-50 transition-all duration-200"
                  >
                    <ChevronLeft className="h-4.5 w-4.5" />
                  </button>
                  <button
                    onClick={() => setMlPage(p => Math.min(p + 1, Math.ceil(mlCount / itemsPerPage)))}
                    disabled={mlPage === Math.ceil(mlCount / itemsPerPage)}
                    className="p-1.5 border border-slate-800 bg-slate-950 text-slate-400 rounded-lg hover:text-white disabled:opacity-50 transition-all duration-200"
                  >
                    <ChevronRight className="h-4.5 w-4.5" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB CONTENT: System Health */}
      {activeTab === 'status' && stats && (
        <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-5 md:p-6 backdrop-blur-md space-y-6">
          <div>
            <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
              <Database className="h-5 w-5 text-blue-400" />
              Infrastructure Status Report
            </h3>
            <p className="text-slate-400 text-xs mt-1">
              Real-time monitoring stats and connectivity diagnostics for the database clusters and ingestion subscriber queues.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="space-y-4">
              <h4 className="text-sm font-bold uppercase tracking-wider text-slate-500">Component Health</h4>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-slate-300">FastAPI Application Server</span>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                    ONLINE
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-slate-300">Supabase DB Engine</span>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-mono">
                    {stats.system_status?.database === 'healthy' ? 'HEALTHY' : 'UNHEALTHY'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-slate-300">ThingSpeak MQTT Ingestion Service</span>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-mono">
                    {stats.system_status?.mqtt_subscriber?.toUpperCase() || 'UNKNOWN'}
                  </span>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <h4 className="text-sm font-bold uppercase tracking-wider text-slate-500">Ingestion Inflows (ThingSpeak MQTT Connection)</h4>

              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3 text-sm text-slate-300">
                <div className="flex justify-between">
                  <span>MQTT Broker Host</span>
                  <span className="font-mono text-xs">mqtt3.thingspeak.com</span>
                </div>
                <div className="flex justify-between">
                  <span>Connection Protocol</span>
                  <span className="text-xs">TCP PubSub (Port 1883)</span>
                </div>
                <div className="flex justify-between">
                  <span>Subscribed Users Channels</span>
                  <span className="font-mono text-xs font-bold text-blue-400">{stats.active_users_count} channels</span>
                </div>
                <div className="flex justify-between">
                  <span>Ingestion Engine Mode</span>
                  <span className="text-xs px-1.5 py-0.25 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded">
                    asyncio-mqtt (always-on)
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function AlertCircle(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="12" x2="12" y1="8" y2="12" />
      <line x1="12" x2="12.01" y1="16" y2="16" />
    </svg>
  )
}
