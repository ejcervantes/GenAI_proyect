import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { Eye, EyeOff, Globe, ArrowRight, Shield } from 'lucide-react'
import toast from 'react-hot-toast'

const FEATURES = ['AI-powered visa Q&A', 'Smart document checklists', 'Live policy alerts']

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '' })
  const [showPw, setShowPw] = useState(false)
  const [loading, setLoading] = useState(false)

  const handle = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      await login(form.email, form.password)
      navigate('/chat')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left panel — decorative */}
      <div className="hidden lg:flex w-[45%] flex-col justify-between p-12 relative overflow-hidden"
        style={{ background: 'linear-gradient(160deg, #08101e 0%, #05080f 100%)', borderRight: '1px solid rgba(180,140,60,0.1)' }}>

        {/* Ambient circles */}
        <div className="absolute top-[-80px] left-[-80px] w-[400px] h-[400px] rounded-full pointer-events-none" style={{ background: 'radial-gradient(circle, rgba(180,140,60,0.06) 0%, transparent 70%)' }} />
        <div className="absolute bottom-[-60px] right-[-60px] w-[300px] h-[300px] rounded-full pointer-events-none" style={{ background: 'radial-gradient(circle, rgba(59,130,246,0.04) 0%, transparent 70%)' }} />

        {/* Globe animation */}
        <div className="absolute right-8 top-1/2 -translate-y-1/2 opacity-5 animate-spin-slow pointer-events-none">
          <Globe size={320} strokeWidth={0.5} />
        </div>

        <div>
          <div className="flex items-center gap-3 mb-16">
            <div className="relative w-11 h-11 flex items-center justify-center">
              <div className="absolute inset-0 rounded-full border border-dashed border-gold-500/40 animate-spin-slow" />
              <Shield size={20} className="text-gold-400 relative z-10" />
            </div>
            <div>
              <p className="font-display text-xl text-white tracking-wide">PassportAI</p>
              <p className="text-[10px] uppercase tracking-[0.2em]" style={{ color: 'rgba(180,140,60,0.55)' }}>Visa Intelligence</p>
            </div>
          </div>

          <h2 className="font-display text-5xl text-white leading-[1.1] mb-6" style={{ fontStyle: 'italic' }}>
            Navigate borders<br/>
            <span className="text-gold-400">with confidence</span>
          </h2>
          <p className="text-slate-500 text-base leading-relaxed max-w-sm">
            AI-powered visa guidance tailored to your passport, destination, and travel purpose.
          </p>
        </div>

        <div className="space-y-3">
          {FEATURES.map((f, i) => (
            <div key={i} className="flex items-center gap-3 animate-fade-up" style={{ animationDelay: `${i * 80}ms` }}>
              <div className="w-1.5 h-1.5 rounded-full bg-gold-400" />
              <p className="text-slate-400 text-sm">{f}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Right panel — form */}
      <div className="flex-1 flex items-center justify-center px-8 py-12">
        <div className="w-full max-w-sm animate-fade-up">
          {/* Mobile logo */}
          <div className="lg:hidden text-center mb-10">
            <p className="font-display text-3xl text-white">PassportAI</p>
            <p className="text-slate-500 text-sm mt-1">Visa intelligence for travellers</p>
          </div>

          <div className="mb-8">
            <h1 className="font-display text-3xl text-white mb-1">Welcome back</h1>
            <p className="text-slate-500 text-sm">Sign in to your account</p>
          </div>

          <form onSubmit={submit} className="space-y-5">
            <div>
              <label className="label">Email</label>
              <input name="email" type="email" required value={form.email}
                onChange={handle} className="input" placeholder="you@example.com" />
            </div>
            <div>
              <label className="label">Password</label>
              <div className="relative">
                <input name="password" type={showPw ? 'text' : 'password'} required
                  value={form.password} onChange={handle} className="input pr-11"
                  placeholder="••••••••" />
                <button type="button" onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-300 transition-colors p-1">
                  {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full justify-center mt-2">
              {loading
                ? <span className="flex items-center gap-2"><span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />Signing in…</span>
                : <span className="flex items-center gap-2">Sign in <ArrowRight size={15} /></span>
              }
            </button>
          </form>

          {/* Divider */}
          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 gold-bar" />
            <p className="text-xs text-slate-600">or</p>
            <div className="flex-1 gold-bar" />
          </div>

          <p className="text-center text-sm text-slate-500">
            No account?{' '}
            <Link to="/register" className="text-gold-400 hover:text-gold-300 font-semibold transition-colors">
              Create one
            </Link>
          </p>

          <p className="text-center text-[11px] text-slate-700 mt-8 leading-relaxed">
            Answers are AI-generated. Always verify with the relevant embassy.
          </p>
        </div>
      </div>
    </div>
  )
}
