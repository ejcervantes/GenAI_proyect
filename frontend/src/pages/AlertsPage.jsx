import { useState, useEffect } from 'react'
import { alertsApi } from '../services/api'
import { Bell, BellOff, RefreshCw, AlertTriangle, Info, Zap, ExternalLink, Loader2, Shield } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'

const SEVERITY_CONFIG = {
  critical: { label: 'Critical', icon: Zap,           cls: 'badge-critical', borderColor: 'rgba(239,68,68,0.25)',  bgColor: 'rgba(239,68,68,0.04)',   dotColor: '#ef4444' },
  warning:  { label: 'Warning',  icon: AlertTriangle,  cls: 'badge-warning',  borderColor: 'rgba(245,158,11,0.25)', bgColor: 'rgba(245,158,11,0.04)',  dotColor: '#f59e0b' },
  info:     { label: 'Info',     icon: Info,            cls: 'badge-info',     borderColor: 'rgba(59,130,246,0.25)', bgColor: 'rgba(59,130,246,0.04)',   dotColor: '#3b82f6' },
}

const CHANGE_TYPE_LABELS = {
  fee_change:       'Fee Change',
  processing_time:  'Processing Time',
  new_requirement:  'New Requirement',
  restriction:      'Restriction',
  general:          'General Update',
}

function AlertCard({ alert, onMarkRead }) {
  const cfg = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.info
  const Icon = cfg.icon
  const [marking, setMarking] = useState(false)

  const markRead = async () => {
    setMarking(true)
    try {
      await alertsApi.markRead(alert.id)
      onMarkRead(alert.id)
    } catch {
      toast.error('Failed to mark as read')
    } finally {
      setMarking(false)
    }
  }

  return (
    <div className={clsx('rounded-2xl overflow-hidden transition-all duration-300 animate-fade-up', alert.is_read && 'opacity-50')}
      style={{
        background: alert.is_read ? 'rgba(12,18,32,0.5)' : cfg.bgColor,
        border: `1px solid ${alert.is_read ? 'rgba(255,255,255,0.05)' : cfg.borderColor}`,
        backdropFilter: 'blur(12px)',
      }}>
      <div className="px-5 py-4">
        <div className="flex items-start gap-4">
          {/* Severity icon */}
          <div className="shrink-0 w-9 h-9 rounded-xl flex items-center justify-center mt-0.5" style={{
            background: cfg.bgColor, border: `1px solid ${cfg.borderColor}`,
          }}>
            <Icon size={15} style={{ color: cfg.dotColor }} />
          </div>

          <div className="flex-1 min-w-0">
            {/* Badges row */}
            <div className="flex items-center gap-2 flex-wrap mb-2">
              <span className={cfg.cls}>{cfg.label}</span>
              <span className="badge-info text-[10px]">{CHANGE_TYPE_LABELS[alert.change_type] || alert.change_type}</span>
              {!alert.is_read && (
                <span className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full font-semibold" style={{
                  background: 'rgba(180,140,60,0.12)', color: '#e8c44a', border: '1px solid rgba(180,140,60,0.2)',
                }}>
                  ● New
                </span>
              )}
            </div>

            <p className="text-sm text-slate-200 leading-relaxed mb-2" style={{ fontFamily: 'Syne' }}>{alert.summary}</p>

            {alert.action_required && (
              <div className="flex items-start gap-2 mt-2 px-3 py-2 rounded-lg" style={{
                background: 'rgba(180,140,60,0.06)', border: '1px solid rgba(180,140,60,0.14)',
              }}>
                <span className="text-gold-500 text-xs mt-0.5 shrink-0">→</span>
                <p className="text-xs text-gold-400/80">{alert.action_required}</p>
              </div>
            )}

            <div className="flex items-center gap-3 mt-3">
              <p className="text-[11px] text-slate-700 font-mono">{new Date(alert.detected_at).toLocaleString()}</p>
              {alert.source_url && (
                <a href={alert.source_url} target="_blank" rel="noopener noreferrer"
                  className="text-[11px] text-slate-600 hover:text-gold-400 flex items-center gap-1 transition-colors">
                  Source <ExternalLink size={9} />
                </a>
              )}
            </div>
          </div>

          {!alert.is_read && (
            <button onClick={markRead} disabled={marking} className="btn-ghost text-xs px-3 py-1.5 shrink-0">
              {marking ? <Loader2 size={11} className="animate-spin" /> : <BellOff size={11} />}
              Mark read
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

const FILTERS = ['all', 'unread', 'critical']

export default function AlertsPage() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [filter, setFilter] = useState('all')

  const load = (params = {}) => {
    alertsApi.list(params)
      .then(r => setAlerts(r.data))
      .catch(() => toast.error('Failed to load alerts'))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    const params = {}
    if (filter === 'unread') params.unread_only = true
    if (filter === 'critical') params.severity = 'critical'
    setLoading(true)
    load(params)
  }, [filter])

  const runNow = async () => {
    setRunning(true)
    try {
      const res = await alertsApi.runNow()
      const d = res.data
      toast.success(`Checked ${d.cases_checked} cases — ${d.changes_found} change(s) found`)
      load()
    } catch {
      toast.error('Check failed')
    } finally {
      setRunning(false)
    }
  }

  const handleMarkRead = (id) => setAlerts(a => a.map(al => al.id === id ? { ...al, is_read: true } : al))
  const unreadCount = alerts.filter(a => !a.is_read).length

  return (
    <div className="p-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-start justify-between mb-8 animate-fade-up">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h1 className="font-display text-3xl text-white">Policy Alerts</h1>
            {unreadCount > 0 && (
              <span className="px-2.5 py-1 rounded-full text-xs font-semibold animate-pulse-gold" style={{
                background: 'rgba(180,140,60,0.15)', color: '#e8c44a',
                border: '1px solid rgba(180,140,60,0.25)', fontFamily: 'Syne',
              }}>
                {unreadCount} new
              </span>
            )}
          </div>
          <p className="text-slate-500 text-sm">Live visa policy changes for your tracked cases</p>
        </div>
        <button onClick={runNow} disabled={running} className="btn-ghost">
          {running ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
          {running ? 'Checking…' : 'Check now'}
        </button>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 mb-6 p-1 rounded-xl w-fit animate-fade-up" style={{
        background: 'rgba(8,14,26,0.8)', border: '1px solid rgba(255,255,255,0.06)',
      }}>
        {FILTERS.map(f => (
          <button key={f} onClick={() => setFilter(f)}
            className="px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-200"
            style={{
              fontFamily: 'Syne',
              background: filter === f ? 'rgba(180,140,60,0.12)' : 'transparent',
              color: filter === f ? '#e8c44a' : 'rgba(148,163,184,0.6)',
              border: filter === f ? '1px solid rgba(180,140,60,0.2)' : '1px solid transparent',
            }}>
            {f.charAt(0).toUpperCase() + f.slice(1)}
          </button>
        ))}
      </div>

      {/* Content */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map(i => <div key={i} className="skeleton h-28 w-full" />)}
        </div>
      ) : alerts.length === 0 ? (
        <div className="rounded-2xl p-16 text-center animate-fade-up" style={{
          background: 'rgba(12,18,32,0.6)', border: '1px solid rgba(255,255,255,0.05)',
        }}>
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4" style={{
            background: 'rgba(180,140,60,0.06)', border: '1px solid rgba(180,140,60,0.12)',
          }}>
            <Bell size={24} className="text-slate-600" />
          </div>
          <p className="text-slate-400 font-semibold mb-1" style={{ fontFamily: 'Syne' }}>No alerts</p>
          <p className="text-slate-600 text-sm">
            {filter === 'all'
              ? 'Policy changes for your tracked visa cases will appear here.'
              : `No ${filter} alerts found.`}
          </p>
        </div>
      ) : (
        <div className="space-y-3 stagger">
          {alerts.map(a => <AlertCard key={a.id} alert={a} onMarkRead={handleMarkRead} />)}
        </div>
      )}
    </div>
  )
}
