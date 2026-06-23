import { useState, useEffect } from 'react'
import { checklistsApi, visaCasesApi } from '../services/api'
import { Plus, CheckCircle2, Circle, AlertCircle, Globe, Loader2, Languages, Stamp, X, ChevronDown, Download, FileText } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'

const PURPOSES = ['student', 'tourist', 'work', 'transit', 'business', 'family']
const PURPOSE_ICONS = { student: '🎓', tourist: '🏖️', work: '💼', transit: '✈️', business: '🤝', family: '👨‍👩‍👧' }

const POPULAR_NATIONALITIES = [
  'Pakistani','Indian','Bangladeshi','Nigerian','Egyptian','Turkish',
  'Iranian','Chinese','Filipino','Indonesian','Brazilian','Moroccan',
]
const POPULAR_DESTINATIONS = [
  'Germany','United States','United Kingdom','Canada','Australia',
  'France','UAE','Japan','Schengen Area','New Zealand','South Korea',
]

function ProgressBar({ items }) {
  if (!items?.length) return null
  const done = items.filter(i => i.is_completed).length
  const pct = Math.round((done / items.length) * 100)
  const color = pct === 100 ? '#10b981' : pct >= 60 ? '#e8c44a' : '#c9a227'
  return (
    <div className="mt-3">
      <div className="flex justify-between text-[11px] mb-1.5" style={{ color: 'rgba(148,163,184,0.6)', fontFamily: 'JetBrains Mono' }}>
        <span>{done} / {items.length} documents</span>
        <span style={{ color }}>{pct}%</span>
      </div>
      <div className="h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
        <div className="h-full rounded-full transition-all duration-700 ease-out" style={{
          width: `${pct}%`,
          background: `linear-gradient(90deg, ${color}aa, ${color})`,
          boxShadow: `0 0 8px ${color}44`,
        }} />
      </div>
    </div>
  )
}

function ChecklistItem({ item, checklistId, onUpdate }) {
  const [toggling, setToggling] = useState(false)

  const toggle = async () => {
    setToggling(true)
    try {
      await checklistsApi.updateItem(checklistId, item.id, { is_completed: !item.is_completed })
      onUpdate()
    } catch {
      toast.error('Failed to update item')
    } finally {
      setToggling(false)
    }
  }

  return (
    <div className={clsx('flex items-start gap-3 p-3 rounded-xl border transition-all duration-200', item.is_completed ? 'opacity-60' : '')}
      style={{
        background: item.is_completed ? 'rgba(16,185,129,0.04)' : 'rgba(255,255,255,0.02)',
        border: item.is_completed ? '1px solid rgba(16,185,129,0.12)' : '1px solid rgba(255,255,255,0.05)',
      }}>
      <button onClick={toggle} disabled={toggling} className="shrink-0 mt-0.5 transition-transform active:scale-90">
        {toggling
          ? <Loader2 size={17} className="text-slate-600 animate-spin" />
          : item.is_completed
            ? <CheckCircle2 size={17} className="text-emerald-400" />
            : <Circle size={17} className="text-slate-700 hover:text-slate-400 transition-colors" />
        }
      </button>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <p className={clsx('text-sm font-medium', item.is_completed ? 'text-slate-600 line-through' : 'text-slate-200')} style={{ fontFamily: 'Syne' }}>
            {item.document_name}
          </p>
          {!item.is_mandatory && <span className="badge-info text-[10px]">Optional</span>}
          {item.is_conditional && <span className="badge-warning text-[10px]">Conditional</span>}
          {item.requires_translation && <Languages size={11} className="text-slate-600" title="Translation required" />}
          {item.requires_notarization && <Stamp size={11} className="text-slate-600" title="Notarization required" />}
        </div>
        {item.description && <p className="text-[11px] text-slate-600 mt-0.5 leading-relaxed">{item.description}</p>}
        {item.condition_note && (
          <p className="text-[11px] mt-1 flex items-center gap-1" style={{ color: 'rgba(245,158,11,0.7)' }}>
            <AlertCircle size={9} />{item.condition_note}
          </p>
        )}
      </div>
    </div>
  )
}

function SectionGroup({ title, items, checklistId, onRefresh, defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen)
  if (!items.length) return null
  return (
    <div>
      <button onClick={() => setOpen(!open)}
        className="flex items-center gap-2 w-full text-left mb-2 group">
        <span className="text-[10px] uppercase tracking-widest font-semibold" style={{ color: 'rgba(180,140,60,0.6)', fontFamily: 'Syne', letterSpacing: '0.15em' }}>
          {title}
        </span>
        <span className="text-[10px] text-slate-700 font-mono">({items.length})</span>
        <ChevronDown size={11} className={clsx('text-slate-700 ml-auto transition-transform', !open && '-rotate-90')} />
      </button>
      {open && (
        <div className="space-y-1.5 animate-fade-in">
          {items.map(item => (
            <ChecklistItem key={item.id} item={item} checklistId={checklistId} onUpdate={onRefresh} />
          ))}
        </div>
      )}
    </div>
  )
}

function ChecklistCard({ checklist, onRefresh }) {
  const mandatory = checklist.items.filter(i => i.is_mandatory && !i.is_conditional)
  const conditional = checklist.items.filter(i => i.is_conditional)
  const optional = checklist.items.filter(i => !i.is_mandatory && !i.is_conditional)
  const done = checklist.items.filter(i => i.is_completed).length
  const total = checklist.items.length
  const [exporting, setExporting] = useState(null) // 'pdf' | 'txt' | null

  const downloadExport = async (format) => {
    setExporting(format)
    try {
      const res = await checklistsApi.export(checklist.id, format)
      const ext = format === 'pdf' ? 'pdf' : 'txt'
      const blob = new Blob([res.data], {
        type: format === 'pdf' ? 'application/pdf' : 'text/plain;charset=utf-8',
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `checklist-${checklist.id}.${ext}`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
    } catch {
      toast.error('Export failed')
    } finally {
      setExporting(null)
    }
  }

  return (
    <div className="rounded-2xl overflow-hidden animate-fade-up" style={{
      background: 'rgba(12,18,32,0.8)',
      border: '1px solid rgba(180,140,60,0.1)',
      backdropFilter: 'blur(12px)',
      boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
    }}>
      {/* Card header */}
      <div className="px-5 py-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h3 className="font-display text-lg text-white leading-tight">{checklist.title}</h3>
            <p className="text-[11px] text-slate-600 mt-0.5 font-mono">
              Generated {new Date(checklist.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            {done === total && total > 0 && (
              <span className="badge-success text-[10px] animate-fade-in">Complete ✓</span>
            )}
            {checklist.confidence_score != null && (
              <span className={clsx('text-[11px] px-2 py-0.5 rounded-md border font-mono',
                checklist.confidence_score >= 0.65 ? 'confidence-high' :
                checklist.confidence_score >= 0.35 ? 'confidence-medium' : 'confidence-low'
              )}>
                {Math.round(checklist.confidence_score * 100)}%
              </span>
            )}
          </div>
        </div>
        <ProgressBar items={checklist.items} />

        {/* Export */}
        <div className="flex items-center gap-2 mt-3">
          <button onClick={() => downloadExport('pdf')} disabled={exporting !== null}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] transition-colors disabled:opacity-50"
            style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', color: 'rgba(148,163,184,0.8)', fontFamily: 'Syne' }}>
            {exporting === 'pdf' ? <Loader2 size={12} className="animate-spin" /> : <Download size={12} />}
            PDF
          </button>
          <button onClick={() => downloadExport('txt')} disabled={exporting !== null}
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] transition-colors disabled:opacity-50"
            style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', color: 'rgba(148,163,184,0.8)', fontFamily: 'Syne' }}>
            {exporting === 'txt' ? <Loader2 size={12} className="animate-spin" /> : <FileText size={12} />}
            Text
          </button>
        </div>
      </div>

      {/* Items */}
      <div className="p-4 space-y-5">
        <SectionGroup title="Required" items={mandatory} checklistId={checklist.id} onRefresh={onRefresh} />
        <SectionGroup title="Conditional" items={conditional} checklistId={checklist.id} onRefresh={onRefresh} />
        <SectionGroup title="Optional / Recommended" items={optional} checklistId={checklist.id} onRefresh={onRefresh} defaultOpen={false} />
      </div>
    </div>
  )
}

// Dropdown for nationality/destination
function SelectDropdown({ value, onChange, placeholder, options, label }) {
  const [open, setOpen] = useState(false)
  const ref = React.useRef(null)

  useEffect(() => {
    const handler = (e) => { if (!ref.current?.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div className="relative" ref={ref}>
      <label className="label">{label}</label>
      <div>
        <input
          className="input"
          placeholder={placeholder}
          value={value}
          onChange={e => onChange(e.target.value)}
          onFocus={() => setOpen(true)}
        />
        {open && (
          <div className="absolute top-full left-0 right-0 mt-1 rounded-xl overflow-hidden z-50 animate-fade-in" style={{
            background: 'rgba(8,14,26,0.98)', border: '1px solid rgba(180,140,60,0.2)',
            backdropFilter: 'blur(20px)', boxShadow: '0 12px 40px rgba(0,0,0,0.6)',
          }}>
            {options.filter(o => o.toLowerCase().includes(value.toLowerCase())).slice(0, 7).map(o => (
              <button key={o} onMouseDown={() => { onChange(o); setOpen(false) }}
                className="w-full text-left px-3 py-2 text-xs text-slate-400 hover:text-gold-400 hover:bg-gold-500/5 transition-colors"
                style={{ fontFamily: 'Syne' }}>
                {o}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

import React from 'react'

export default function ChecklistPage() {
  const [checklists, setChecklists] = useState([])
  const [pageLoading, setPageLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ passport_nationality: '', destination_country: '', travel_purpose: '' })

  const load = () => {
    checklistsApi.list()
      .then(r => setChecklists(r.data))
      .catch(() => toast.error('Failed to load checklists'))
      .finally(() => setPageLoading(false))
  }

  useEffect(() => { load() }, [])

  const generate = async (e) => {
    e.preventDefault()
    if (!form.passport_nationality || !form.destination_country || !form.travel_purpose) {
      toast.error('Please fill all three fields'); return
    }
    setGenerating(true)
    try {
      await checklistsApi.generate(form)
      toast.success('Checklist generated!')
      setShowForm(false)
      setForm({ passport_nationality: '', destination_country: '', travel_purpose: '' })
      load()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Generation failed')
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="p-6 max-w-3xl">
      {/* Header */}
      <div className="flex items-start justify-between mb-8 animate-fade-up">
        <div>
          <h1 className="font-display text-3xl text-white mb-1">Document Checklists</h1>
          <p className="text-slate-500 text-sm">AI-generated, personalised document lists for your visa application</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className={showForm ? 'btn-ghost' : 'btn-primary'}>
          {showForm ? <><X size={14} /> Cancel</> : <><Plus size={14} /> New Checklist</>}
        </button>
      </div>

      {/* Generate form */}
      {showForm && (
        <div className="rounded-2xl p-6 mb-8 animate-fade-up" style={{
          background: 'rgba(12,18,32,0.9)', border: '1px solid rgba(180,140,60,0.18)',
          backdropFilter: 'blur(12px)', boxShadow: '0 0 40px rgba(180,140,60,0.06)',
        }}>
          <p className="text-sm font-semibold text-white mb-5" style={{ fontFamily: 'Syne' }}>
            Generate a new checklist
          </p>
          <form onSubmit={generate}>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <SelectDropdown
                label="Your Passport"
                placeholder="e.g. Pakistani"
                value={form.passport_nationality}
                onChange={v => setForm(f => ({ ...f, passport_nationality: v }))}
                options={POPULAR_NATIONALITIES}
              />
              <SelectDropdown
                label="Destination"
                placeholder="e.g. Germany"
                value={form.destination_country}
                onChange={v => setForm(f => ({ ...f, destination_country: v }))}
                options={POPULAR_DESTINATIONS}
              />
            </div>

            <div className="mb-5">
              <label className="label">Travel Purpose</label>
              <div className="grid grid-cols-3 gap-2">
                {PURPOSES.map(p => (
                  <button key={p} type="button" onClick={() => setForm(f => ({ ...f, travel_purpose: p }))}
                    className="py-2.5 px-3 rounded-xl text-xs font-medium transition-all duration-150 flex items-center justify-center gap-1.5"
                    style={{
                      fontFamily: 'Syne',
                      background: form.travel_purpose === p ? 'rgba(180,140,60,0.16)' : 'rgba(255,255,255,0.02)',
                      border: form.travel_purpose === p ? '1px solid rgba(180,140,60,0.35)' : '1px solid rgba(255,255,255,0.06)',
                      color: form.travel_purpose === p ? '#e8c44a' : 'rgba(148,163,184,0.6)',
                    }}>
                    <span>{PURPOSE_ICONS[p]}</span>
                    {p.charAt(0).toUpperCase() + p.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            <button type="submit" disabled={generating} className="btn-primary">
              {generating
                ? <><Loader2 size={14} className="animate-spin" />Generating…</>
                : <>Generate Checklist</>
              }
            </button>
          </form>
        </div>
      )}

      {/* List */}
      {pageLoading ? (
        <div className="space-y-4">
          {[1, 2].map(i => <div key={i} className="skeleton h-52 w-full" />)}
        </div>
      ) : checklists.length === 0 ? (
        <div className="rounded-2xl p-16 text-center animate-fade-up" style={{
          background: 'rgba(12,18,32,0.6)', border: '1px solid rgba(255,255,255,0.05)',
        }}>
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4 animate-float" style={{
            background: 'rgba(180,140,60,0.06)', border: '1px solid rgba(180,140,60,0.12)',
          }}>
            <Globe size={24} className="text-slate-600" />
          </div>
          <p className="text-slate-400 font-semibold mb-1" style={{ fontFamily: 'Syne' }}>No checklists yet</p>
          <p className="text-slate-600 text-sm mb-5">Generate one for your visa application above.</p>
          <button onClick={() => setShowForm(true)} className="btn-primary text-sm">
            <Plus size={14} /> Create your first checklist
          </button>
        </div>
      ) : (
        <div className="space-y-5 stagger">
          {checklists.map(cl => <ChecklistCard key={cl.id} checklist={cl} onRefresh={load} />)}
        </div>
      )}
    </div>
  )
}
