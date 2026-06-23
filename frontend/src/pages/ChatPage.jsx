import { useState, useRef, useEffect } from 'react'
import { chatApi } from '../services/api'
import { Send, Bot, User, BookOpen, AlertTriangle, ChevronDown, ChevronUp, Sparkles, Globe } from 'lucide-react'
import toast from 'react-hot-toast'
import clsx from 'clsx'

const PURPOSES = ['student', 'tourist', 'work', 'transit', 'business', 'family']

const PURPOSE_ICONS = {
  student: '🎓', tourist: '🏖️', work: '💼', transit: '✈️', business: '🤝', family: '👨‍👩‍👧'
}

// Popular countries for quick select
const POPULAR_COUNTRIES = [
  'Germany', 'United States', 'United Kingdom', 'Canada', 'Australia',
  'France', 'UAE', 'Japan', 'Schengen Area', 'New Zealand'
]

const POPULAR_PASSPORTS = [
  'Pakistani', 'Indian', 'Bangladeshi', 'Nigerian', 'Egyptian',
  'Turkish', 'Iranian', 'Chinese', 'Filipino', 'Indonesian'
]

function ConfidencePill({ label, score }) {
  return (
    <span className={clsx(
      'inline-flex items-center gap-1 px-2 py-0.5 rounded-md border text-[11px] font-medium',
      label === 'high'   && 'confidence-high',
      label === 'medium' && 'confidence-medium',
      label === 'low'    && 'confidence-low',
    )} style={{ fontFamily: 'JetBrains Mono' }}>
      {Math.round(score * 100)}% confidence
    </span>
  )
}

function CitationList({ citations }) {
  const [open, setOpen] = useState(false)
  if (!citations?.length) return null
  return (
    <div className="mt-3">
      <button onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-xs text-slate-600 hover:text-gold-400 transition-colors">
        <BookOpen size={11} />
        {citations.length} source{citations.length > 1 ? 's' : ''}
        {open ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
      </button>
      {open && (
        <ul className="mt-2 space-y-1 animate-fade-in">
          {citations.map((c, i) => (
            <li key={i} className="text-[11px] text-slate-600 flex items-start gap-2">
              <span className="text-gold-600 shrink-0 font-mono">[{i + 1}]</span>
              <span>{c.title} — <span className="text-slate-700">{c.last_scraped}</span></span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Message({ msg, isNew }) {
  const isUser = msg.role === 'user'
  return (
    <div className={clsx('flex gap-3 animate-fade-up', isUser && 'flex-row-reverse')}>
      {/* Avatar */}
      <div className={clsx(
        'shrink-0 w-8 h-8 rounded-xl flex items-center justify-center text-xs',
        isUser
          ? 'text-gold-400'
          : 'text-slate-400'
      )} style={{
        background: isUser ? 'rgba(180,140,60,0.12)' : 'rgba(255,255,255,0.04)',
        border: isUser ? '1px solid rgba(180,140,60,0.2)' : '1px solid rgba(255,255,255,0.07)',
      }}>
        {isUser ? <User size={13} /> : <Bot size={13} />}
      </div>

      <div className={clsx('max-w-[76%]', isUser && 'items-end flex flex-col')}>
        <div className={clsx('rounded-2xl px-4 py-3 text-sm leading-relaxed')} style={
          isUser
            ? { background: 'rgba(180,140,60,0.09)', border: '1px solid rgba(180,140,60,0.16)', color: '#e2e8f0' }
            : { background: 'rgba(12,18,32,0.9)', border: '1px solid rgba(255,255,255,0.07)', color: '#cbd5e1' }
        }>
          <p className="whitespace-pre-wrap" style={{ fontFamily: 'Syne', fontSize: '13.5px', lineHeight: '1.65' }}>
            {msg.content.replace(/\*\*(.*?)\*\*/g, '$1')}
          </p>
        </div>

        {msg.confidence_score !== undefined && (
          <div className="flex items-center gap-2 mt-1.5 px-1">
            <ConfidencePill label={msg.confidence_label} score={msg.confidence_score} />
            {msg.confidence_label === 'low' && (
              <span className="flex items-center gap-1 text-[11px] text-amber-400">
                <AlertTriangle size={10} /> Verify with embassy
              </span>
            )}
          </div>
        )}
        {msg.citations && <CitationList citations={msg.citations} />}
      </div>
    </div>
  )
}

function TypingDots() {
  return (
    <div className="flex gap-3 animate-fade-in">
      <div className="shrink-0 w-8 h-8 rounded-xl flex items-center justify-center" style={{
        background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.07)',
      }}>
        <Bot size={13} className="text-slate-500" />
      </div>
      <div className="rounded-2xl px-4 py-3 flex gap-1.5 items-center" style={{
        background: 'rgba(12,18,32,0.9)', border: '1px solid rgba(255,255,255,0.07)',
      }}>
        {[0, 160, 320].map(d => (
          <span key={d} className="w-1.5 h-1.5 rounded-full bg-gold-500 animate-bounce"
            style={{ animationDelay: `${d}ms` }} />
        ))}
      </div>
    </div>
  )
}

// Combobox with dropdown suggestions
function CountryCombobox({ value, onChange, placeholder, suggestions }) {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    const handler = (e) => { if (!ref.current?.contains(e.target)) setOpen(false) }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const filtered = suggestions.filter(s => s.toLowerCase().includes(value.toLowerCase()) && s !== value)

  return (
    <div className="relative" ref={ref}>
      <input
        className="input text-xs py-2"
        placeholder={placeholder}
        value={value}
        onChange={e => onChange(e.target.value)}
        onFocus={() => setOpen(true)}
      />
      {open && filtered.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 rounded-xl overflow-hidden z-50 animate-fade-in" style={{
          background: 'rgba(8,14,26,0.98)',
          border: '1px solid rgba(180,140,60,0.2)',
          backdropFilter: 'blur(20px)',
          boxShadow: '0 12px 40px rgba(0,0,0,0.6)',
        }}>
          {filtered.slice(0, 6).map(s => (
            <button key={s} onMouseDown={() => { onChange(s); setOpen(false) }}
              className="w-full text-left px-3 py-2 text-xs text-slate-400 hover:text-gold-400 hover:bg-gold-500/5 transition-colors"
              style={{ fontFamily: 'Syne' }}>
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

const QUICK_PROMPTS = [
  'What documents do I need for a student visa?',
  'How long does a Schengen visa take to process?',
  'Can I work on a tourist visa?',
]

export default function ChatPage() {
  const [messages, setMessages] = useState([{
    id: 0, role: 'assistant',
    content: 'Hello! I can answer questions about visa requirements, document checklists, and processing times. Set your travel context on the right to get more precise answers.',
  }])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [context, setContext] = useState({ passport_nationality: '', destination_country: '', travel_purpose: '' })
  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const send = async (text) => {
    const question = (text ?? input).trim()
    if (!question || loading) return
    setInput('')
    setMessages(m => [...m, { id: Date.now(), role: 'user', content: question }])
    setLoading(true)
    try {
      const payload = { question, ...Object.fromEntries(Object.entries(context).filter(([, v]) => v)) }
      const res = await chatApi.ask(payload)
      const d = res.data
      setMessages(m => [...m, {
        id: d.interaction_id, role: 'assistant',
        content: d.answer, confidence_score: d.confidence_score,
        confidence_label: d.confidence_label, citations: d.citations,
      }])
    } catch {
      toast.error('Failed to get answer. Please try again.')
      setMessages(m => m.slice(0, -1))
      setInput(question)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e) => { e.preventDefault(); send() }

  const contextSet = context.passport_nationality || context.destination_country || context.travel_purpose

  return (
    <div className="flex h-screen">
      {/* ── Chat ── */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="px-6 py-4 shrink-0 flex items-center justify-between" style={{
          borderBottom: '1px solid rgba(180,140,60,0.08)',
          background: 'rgba(5,8,15,0.6)',
          backdropFilter: 'blur(12px)',
        }}>
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{
              background: 'rgba(180,140,60,0.1)', border: '1px solid rgba(180,140,60,0.2)',
            }}>
              <Sparkles size={14} className="text-gold-400" />
            </div>
            <div>
              <h1 className="font-display text-lg text-white">Visa Q&A</h1>
              <p className="text-[11px] text-slate-600">Ask anything about visa requirements</p>
            </div>
          </div>
          {contextSet && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg animate-fade-in" style={{
              background: 'rgba(180,140,60,0.06)', border: '1px solid rgba(180,140,60,0.14)',
            }}>
              <Globe size={11} className="text-gold-500" />
              <span className="text-[11px] text-gold-500/80">Context set</span>
            </div>
          )}
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
          {messages.map((m, i) => <Message key={m.id} msg={m} isNew={i === messages.length - 1} />)}
          {loading && <TypingDots />}
          <div ref={bottomRef} />
        </div>

        {/* Quick prompts (only when empty) */}
        {messages.length === 1 && !loading && (
          <div className="px-6 pb-2 flex gap-2 flex-wrap animate-fade-up">
            {QUICK_PROMPTS.map(q => (
              <button key={q} onClick={() => send(q)}
                className="text-xs text-slate-500 hover:text-gold-400 px-3 py-1.5 rounded-lg transition-all duration-200"
                style={{ border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.02)', fontFamily: 'Syne' }}>
                {q}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <div className="px-6 pb-5 pt-3 shrink-0" style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
          <form onSubmit={handleSubmit} className="flex gap-3">
            <input
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              className="input flex-1"
              placeholder="e.g. What documents do I need for a student visa?"
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), send())}
            />
            <button type="submit" disabled={loading || !input.trim()} className="btn-primary px-4 shrink-0">
              <Send size={14} />
            </button>
          </form>
        </div>
      </div>

      {/* ── Context panel ── */}
      <aside className="w-60 shrink-0 flex flex-col" style={{
        borderLeft: '1px solid rgba(180,140,60,0.08)',
        background: 'rgba(8,14,26,0.6)',
        backdropFilter: 'blur(12px)',
      }}>
        <div className="p-5 flex-1 flex flex-col gap-5 overflow-y-auto">
          {/* Header */}
          <div>
            <div className="flex items-center gap-2 mb-1">
              <Globe size={12} className="text-gold-500" />
              <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'rgba(180,140,60,0.8)', fontFamily: 'Syne', letterSpacing: '0.15em' }}>
                Travel Context
              </p>
            </div>
            <p className="text-[11px] text-slate-600 leading-relaxed mt-2">
              Set your details for personalised, accurate answers.
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="label text-[10px]">Your Passport</label>
              <CountryCombobox
                value={context.passport_nationality}
                onChange={v => setContext(c => ({ ...c, passport_nationality: v }))}
                placeholder="e.g. Pakistani"
                suggestions={POPULAR_PASSPORTS}
              />
            </div>

            <div>
              <label className="label text-[10px]">Destination</label>
              <CountryCombobox
                value={context.destination_country}
                onChange={v => setContext(c => ({ ...c, destination_country: v }))}
                placeholder="e.g. Germany"
                suggestions={POPULAR_COUNTRIES}
              />
            </div>

            <div>
              <label className="label text-[10px]">Purpose</label>
              <div className="grid grid-cols-2 gap-1.5">
                {PURPOSES.map(p => (
                  <button key={p} onClick={() => setContext(c => ({ ...c, travel_purpose: c.travel_purpose === p ? '' : p }))}
                    className={clsx(
                      'px-2 py-2 rounded-lg text-[11px] font-medium transition-all duration-150 text-center',
                    )}
                    style={{
                      fontFamily: 'Syne',
                      background: context.travel_purpose === p ? 'rgba(180,140,60,0.14)' : 'rgba(255,255,255,0.02)',
                      border: context.travel_purpose === p ? '1px solid rgba(180,140,60,0.3)' : '1px solid rgba(255,255,255,0.06)',
                      color: context.travel_purpose === p ? '#e8c44a' : 'rgba(148,163,184,0.7)',
                    }}>
                    {PURPOSE_ICONS[p]} {p.charAt(0).toUpperCase() + p.slice(1)}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="gold-bar" />

          <p className="text-[10px] leading-relaxed" style={{ color: 'rgba(100,116,139,0.6)' }}>
            Answers are AI-generated from official policy sources. Always verify with the relevant embassy before applying.
          </p>
        </div>
      </aside>
    </div>
  )
}
