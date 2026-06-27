import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans relative overflow-hidden">
      {/* Background radial glow */}
      <div className="absolute top-[-10%] left-[20%] w-[600px] h-[600px] bg-blue-500/10 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-[-10%] right-[10%] w-[500px] h-[500px] bg-cyan-500/10 rounded-full blur-[100px] pointer-events-none" />

      {/* Header */}
      <header className="w-full max-w-7xl mx-auto px-6 h-20 flex items-center justify-between border-b border-slate-900/60 backdrop-blur-md z-10">
        <div className="flex items-center gap-3">
          <span className="text-2xl font-black bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-teal-300 to-cyan-400">
            AquaSense
          </span>
          <span className="text-[10px] uppercase font-bold tracking-wider px-2.5 py-0.5 bg-blue-500/10 text-blue-400 rounded-full border border-blue-500/20">
            v3.1
          </span>
        </div>
        <div className="flex items-center gap-4">
          <Link
            href="/login"
            className="text-sm font-medium text-slate-400 hover:text-white transition-colors duration-200"
          >
            Sign In
          </Link>
          <Link
            href="/signup"
            className="text-sm font-medium px-4.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold shadow-lg shadow-blue-600/20 hover:shadow-blue-500/30 transition-all duration-200"
          >
            Get Started
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <main className="flex-1 max-w-7xl mx-auto px-6 flex flex-col items-center justify-center text-center py-20 z-10">
        <div className="max-w-3xl space-y-6">
          <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-[1.15]">
            Real-Time IoT
            <span className="block mt-2 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-cyan-300 to-teal-400">
              Water Quality Intelligence
            </span>
          </h1>
          <p className="text-lg sm:text-xl text-slate-400 leading-relaxed max-w-2xl mx-auto">
            Monitor and secure water resources with high-frequency telemetry, edge integration, and predictive machine learning diagnostics.
          </p>
          <div className="pt-6 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/dashboard"
              className="w-full sm:w-auto flex items-center justify-center gap-2 px-8 py-3.5 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 hover:from-blue-600 hover:to-cyan-600 text-slate-950 font-bold shadow-lg shadow-blue-500/25 transition-all duration-300 transform hover:-translate-y-0.5"
            >
              Enter Dashboard
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
              </svg>
            </Link>
            <Link
              href="/signup"
              className="w-full sm:w-auto flex items-center justify-center px-8 py-3.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-200 hover:bg-slate-800/80 hover:text-white transition-all duration-200"
            >
              Create Account
            </Link>
          </div>
        </div>

        {/* Feature Grid */}
        <section className="mt-28 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 w-full text-left">
          {/* Card 1 */}
          <div className="p-6 bg-slate-900/40 border border-slate-900 rounded-2xl backdrop-blur-md hover:border-slate-800 transition-all duration-200 group">
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 mb-5 group-hover:scale-110 transition-transform duration-200">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-white mb-2">High-Frequency Telemetry</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Ingest sensor updates (pH, TDS, Turbidity) using low-latency MQTT brokers and view immediate updates pushed via SSE streams.
            </p>
          </div>

          {/* Card 2 */}
          <div className="p-6 bg-slate-900/40 border border-slate-900 rounded-2xl backdrop-blur-md hover:border-slate-800 transition-all duration-200 group">
            <div className="w-12 h-12 rounded-xl bg-teal-500/10 border border-teal-500/20 flex items-center justify-center text-teal-400 mb-5 group-hover:scale-110 transition-transform duration-200">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2m0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Predictive ML Diagnostics</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              XGBoost classifier predicts safety status (Safe, Borderline, Unsafe) with exact SHAP tree values detailing parameter contributions.
            </p>
          </div>

          {/* Card 3 */}
          <div className="p-6 bg-slate-900/40 border border-slate-900 rounded-2xl backdrop-blur-md hover:border-slate-800 transition-all duration-200 group">
            <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 mb-5 group-hover:scale-110 transition-transform duration-200">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Statistical Anomaly Engine</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Isolation Forest model scans telemetry against EWMA-smoothed parameters to detect sensor drift, errors, and system anomalies.
            </p>
          </div>

          {/* Card 4 */}
          <div className="p-6 bg-slate-900/40 border border-slate-900 rounded-2xl backdrop-blur-md hover:border-slate-800 transition-all duration-200 group">
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 mb-5 group-hover:scale-110 transition-transform duration-200">
              <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
              </svg>
            </div>
            <h3 className="text-lg font-bold text-white mb-2">Actionable Alerts</h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Get notified immediately of abnormal readings with clear classifications, severity markers, and actionable recommendations.
            </p>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="w-full py-8 text-center text-xs text-slate-600 border-t border-slate-900/60 z-10">
        <p>© 2026 AquaSense System. All rights reserved.</p>
      </footer>
    </div>
  );
}
