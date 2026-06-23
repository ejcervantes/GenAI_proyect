import { useState, useRef } from 'react'
import { documentsApi } from '../services/api'
import { Upload, ScanLine, AlertTriangle, CheckCircle2, Download, FileText, Loader2, Sparkles } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'

const DOC_TYPES = [
  { value: 'passport',    label: 'Passport',    icon: '🛂' },
  { value: 'national_id', label: 'National ID',  icon: '🪪' },
]

function ConfidenceDot({ score }) {
  const color = score >= 0.85 ? '#10b981' : score >= 0.75 ? '#f59e0b' : '#ef4444'
  return (
    <span className="inline-block w-2 h-2 rounded-full shrink-0" style={{ background: color }}
      title={`${Math.round(score * 100)}% confidence`} />
  )
}

function FieldTable({ fields, fieldConfidence, flaggedFields }) {
  if (!fields || Object.keys(fields).length === 0) return null
  return (
    <div className="rounded-xl overflow-hidden" style={{ border: '1px solid rgba(255,255,255,0.06)' }}>
      <table className="w-full text-sm">
        <thead>
          <tr style={{ background: 'rgba(255,255,255,0.03)', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
            <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-widest font-semibold w-40" style={{ color: 'rgba(180,140,60,0.5)' }}>Field</th>
            <th className="text-left px-4 py-2.5 text-[10px] uppercase tracking-widest font-semibold" style={{ color: 'rgba(180,140,60,0.5)' }}>Value</th>
            <th className="text-right px-4 py-2.5 text-[10px] uppercase tracking-widest font-semibold w-24" style={{ color: 'rgba(180,140,60,0.5)' }}>Conf.</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(fields).map(([key, value], i) => {
            const score = fieldConfidence?.[key] ?? 1
            const flagged = flaggedFields?.includes(key)
            return (
              <tr key={key} style={{
                borderBottom: '1px solid rgba(255,255,255,0.04)',
                background: flagged ? 'rgba(245,158,11,0.04)' : i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.01)',
              }}>
                <td className="px-4 py-2.5">
                  <span className="text-slate-500 text-[11px]" style={{ fontFamily: 'JetBrains Mono' }}>
                    {key.replace(/_/g, ' ')}
                  </span>
                </td>
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-200 text-sm font-medium" style={{ fontFamily: 'Syne' }}>{String(value)}</span>
                    {flagged && <AlertTriangle size={11} className="text-amber-400 shrink-0" title="Low confidence — verify" />}
                  </div>
                </td>
                <td className="px-4 py-2.5 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <ConfidenceDot score={score} />
                    <span className="text-[11px] text-slate-600" style={{ fontFamily: 'JetBrains Mono' }}>{Math.round(score * 100)}%</span>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function DropZone({ onFile, label, accept, icon: Icon, active }) {
  const ref = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [filename, setFilename] = useState(null)

  const handle = (file) => {
    if (!file) return
    setFilename(file.name)
    onFile(file)
  }

  return (
    <div
      onClick={() => ref.current.click()}
      onDragOver={e => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={e => { e.preventDefault(); setDragging(false); handle(e.dataTransfer.files[0]) }}
      className="relative border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-200"
      style={{
        borderColor: dragging ? 'rgba(180,140,60,0.7)' : filename ? 'rgba(16,185,129,0.4)' : 'rgba(255,255,255,0.08)',
        background: dragging ? 'rgba(180,140,60,0.06)' : filename ? 'rgba(16,185,129,0.04)' : 'rgba(255,255,255,0.01)',
      }}
    >
      <input ref={ref} type="file" accept={accept} className="hidden"
        onChange={e => handle(e.target.files[0])} />

      {/* Upload icon */}
      <div className="w-12 h-12 rounded-xl flex items-center justify-center mx-auto mb-3 transition-all duration-200" style={{
        background: dragging ? 'rgba(180,140,60,0.12)' : filename ? 'rgba(16,185,129,0.1)' : 'rgba(255,255,255,0.04)',
        border: `1px solid ${dragging ? 'rgba(180,140,60,0.3)' : filename ? 'rgba(16,185,129,0.2)' : 'rgba(255,255,255,0.07)'}`,
      }}>
        {filename
          ? <CheckCircle2 size={22} className="text-emerald-400" />
          : <Icon size={22} style={{ color: dragging ? '#e8c44a' : 'rgba(148,163,184,0.4)' }} />
        }
      </div>

      {filename
        ? <p className="text-sm font-semibold text-emerald-400" style={{ fontFamily: 'Syne' }}>{filename}</p>
        : <>
            <p className="text-sm text-slate-500" style={{ fontFamily: 'Syne' }}>{label}</p>
            <p className="text-[11px] text-slate-700 mt-1">Click or drag & drop</p>
          </>
      }
    </div>
  )
}

function StepNumber({ n, done }) {
  return (
    <div className="w-8 h-8 rounded-xl flex items-center justify-center text-xs font-bold transition-all duration-300" style={{
      background: done ? 'rgba(16,185,129,0.12)' : 'rgba(180,140,60,0.1)',
      border: `1px solid ${done ? 'rgba(16,185,129,0.25)' : 'rgba(180,140,60,0.25)'}`,
      color: done ? '#10b981' : '#e8c44a',
      fontFamily: 'Syne',
    }}>
      {done ? '✓' : n}
    </div>
  )
}

export default function ScannerPage() {
  const [docType, setDocType] = useState('passport')
  const [scanFile, setScanFile] = useState(null)
  const [scanning, setScanning] = useState(false)
  const [scanResult, setScanResult] = useState(null)

  const [formFile, setFormFile] = useState(null)
  const [filling, setFilling] = useState(false)
  const [fillResult, setFillResult] = useState(null)

  const runScan = async () => {
    if (!scanFile) { toast.error('Please select a file first'); return }
    setScanning(true)
    setScanResult(null)
    try {
      const fd = new FormData()
      fd.append('file', scanFile)
      fd.append('document_type', docType)
      const res = await documentsApi.scan(fd)
      setScanResult(res.data)
      toast.success('Document scanned successfully')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Scan failed')
    } finally {
      setScanning(false)
    }
  }

  const runFill = async () => {
    if (!formFile) { toast.error('Please upload a blank form first'); return }
    if (!scanResult) { toast.error('Scan a passport first to supply personal data'); return }
    setFilling(true)
    setFillResult(null)
    try {
      const fd = new FormData()
      fd.append('file', formFile)
      const res = await documentsApi.fill(scanResult.id, fd)
      setFillResult(res.data)
      toast.success('Form filled!')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Form fill failed')
    } finally {
      setFilling(false)
    }
  }

  return (
    <div className="p-6 max-w-3xl space-y-6">
      {/* Header */}
      <div className="animate-fade-up">
        <h1 className="font-display text-3xl text-white mb-1">Document Scanner</h1>
        <p className="text-slate-500 text-sm">Extract passport data and auto-fill visa application forms</p>
      </div>

      {/* Step 1 */}
      <section className="rounded-2xl overflow-hidden animate-fade-up" style={{
        background: 'rgba(12,18,32,0.8)', border: '1px solid rgba(180,140,60,0.1)',
        backdropFilter: 'blur(12px)', animationDelay: '60ms',
      }}>
        {/* Section header */}
        <div className="px-6 py-4 flex items-center gap-3" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <StepNumber n={1} done={!!scanResult} />
          <div>
            <h2 className="font-display text-base text-white">Scan Identity Document</h2>
            <p className="text-[11px] text-slate-600">Upload your passport or national ID</p>
          </div>
        </div>

        <div className="p-6">
          {/* Doc type selector */}
          <div className="flex gap-2 mb-5">
            {DOC_TYPES.map(t => (
              <button key={t.value} onClick={() => setDocType(t.value)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-150"
                style={{
                  fontFamily: 'Syne',
                  background: docType === t.value ? 'rgba(180,140,60,0.12)' : 'rgba(255,255,255,0.02)',
                  border: docType === t.value ? '1px solid rgba(180,140,60,0.3)' : '1px solid rgba(255,255,255,0.06)',
                  color: docType === t.value ? '#e8c44a' : 'rgba(148,163,184,0.6)',
                }}>
                {t.icon} {t.label}
              </button>
            ))}
          </div>

          <DropZone onFile={setScanFile} label="Upload passport or ID (JPEG, PNG, PDF)"
            accept="image/jpeg,image/png,image/webp,application/pdf" icon={ScanLine} />

          <button onClick={runScan} disabled={!scanFile || scanning} className="btn-primary mt-4">
            {scanning
              ? <><Loader2 size={14} className="animate-spin" />Scanning…</>
              : <><ScanLine size={14} />Scan Document</>
            }
          </button>

          {/* Scan result */}
          {scanResult && (
            <div className="mt-6 animate-fade-up">
              <div className="gold-bar mb-5" />

              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <Sparkles size={14} className="text-gold-400" />
                  <p className="text-sm font-semibold text-white" style={{ fontFamily: 'Syne' }}>Extraction complete</p>
                </div>
                <span className={clsx(
                  'text-[11px] px-2.5 py-1 rounded-md border font-mono',
                  scanResult.extraction_confidence >= 0.85 ? 'confidence-high' :
                  scanResult.extraction_confidence >= 0.70 ? 'confidence-medium' : 'confidence-low'
                )}>
                  {Math.round((scanResult.extraction_confidence ?? 0) * 100)}% overall
                </span>
              </div>

              {scanResult.flagged_fields?.length > 0 && (
                <div className="flex items-start gap-2 p-3 rounded-xl mb-4" style={{
                  background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.2)',
                }}>
                  <AlertTriangle size={13} className="text-amber-400 shrink-0 mt-0.5" />
                  <p className="text-xs text-amber-300/80">
                    Low confidence on: <strong className="text-amber-300">{scanResult.flagged_fields.join(', ')}</strong>. Please verify manually.
                  </p>
                </div>
              )}

              <FieldTable fields={scanResult.fields} fieldConfidence={scanResult.field_confidence} flaggedFields={scanResult.flagged_fields} />
            </div>
          )}
        </div>
      </section>

      {/* Step 2 */}
      <section className={clsx('rounded-2xl overflow-hidden transition-all duration-500 animate-fade-up', !scanResult && 'opacity-40 pointer-events-none')}
        style={{
          background: 'rgba(12,18,32,0.8)', border: '1px solid rgba(180,140,60,0.1)',
          backdropFilter: 'blur(12px)', animationDelay: '120ms',
        }}>
        <div className="px-6 py-4 flex items-center gap-3" style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <StepNumber n={2} done={!!fillResult} />
          <div>
            <h2 className="font-display text-base text-white">Fill Visa Application Form</h2>
            <p className="text-[11px] text-slate-600">{!scanResult ? 'Complete step 1 first' : 'Upload a blank form to auto-fill'}</p>
          </div>
        </div>

        <div className="p-6">
          <DropZone onFile={setFormFile} label="Upload blank visa form (PDF or DOCX)"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            icon={FileText} />

          <button onClick={runFill} disabled={!formFile || !scanResult || filling} className="btn-primary mt-4">
            {filling
              ? <><Loader2 size={14} className="animate-spin" />Filling…</>
              : <><FileText size={14} />Fill Form</>
            }
          </button>

          {fillResult && (
            <div className="mt-6 animate-fade-up">
              <div className="gold-bar mb-5" />
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <CheckCircle2 size={15} className="text-emerald-400" />
                  <p className="text-sm font-semibold text-white" style={{ fontFamily: 'Syne' }}>
                    {Object.keys(fillResult.filled_fields ?? {}).length} fields filled
                    {fillResult.unfilled_fields?.length > 0 &&
                      <span className="text-amber-400 ml-2 font-normal">· {fillResult.unfilled_fields.length} unfilled</span>}
                  </p>
                </div>
                <a href={documentsApi.downloadUrl(fillResult.id)} className="btn-primary text-xs px-3 py-1.5" download>
                  <Download size={12} /> Download
                </a>
              </div>
              {fillResult.unfilled_fields?.length > 0 && (
                <div className="p-3 rounded-xl text-xs" style={{
                  background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.2)', color: 'rgba(252,211,77,0.8)',
                }}>
                  Fields not filled (highlighted in document): {fillResult.unfilled_fields.join(', ')}
                </div>
              )}
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
