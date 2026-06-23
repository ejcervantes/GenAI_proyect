import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../services/api'
import { useAuth } from '../context/AuthContext'
import { Shield, ArrowRight, Globe } from 'lucide-react'
import toast from 'react-hot-toast'

export default function RegisterPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ email: '', password: '', full_name: '' })
  const [loading, setLoading] = useState(false)

  const handle = (e) => setForm({ ...form, [e.target.name]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    if (form.password.length < 8) { toast.error('Password must be at least 8 characters'); return }
    setLoading(true)
    try {
      await authApi.register(form)
      await login(form.email, form.password)
      navigate('/chat')
      toast.success('Account created — welcome!')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Left decorative panel */}
      <div className="hidden lg:flex w-[45%] flex-col justify-center p-12 relative overflow-hidden"
        style={{ background: 'linear-gradient(160deg, #08101e 0%, #05080f 100%)', borderRight: '1px solid rgba(180,140,60,0.1)' }}>

        <div className="absolute top-[-80px] right-[-80px] w-[400px] h-[400px] rounded-full pointer-events-none" style={{ background: 'radial-gradient(circle, rgba(180,140,60,0.06) 0%, transparent 70%)' }} />

        <div className="absolute left-8 top-1/2 -translate-y-1/2 opacity-5 animate-spin-slow pointer-events-none" style={{ animationDirection: 'reverse' }}>
          <Globe size={280} strokeWidth={0.5} />
        </div>

        <div className="flex items-center gap-3 mb-12">
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
          Your journey<br/>
          <span className="text-gold-400">starts here</span>
        </h2>
        <p className="text-slate-500 text-base leading-relaxed max-w-sm">
          Join thousands of travellers who use PassportAI to navigate complex visa requirements with ease.
        </p>
      </div>

      {/* Right form panel */}
      <div className="flex-1 flex items-center justify-center px-8 py-12">
        <div className="w-full max-w-sm animate-fade-up">

          <div className="mb-8">
            <h1 className="font-display text-3xl text-white mb-1">Create account</h1>
            <p className="text-slate-500 text-sm">Start your visa intelligence journey</p>
          </div>

          <form onSubmit={submit} className="space-y-5">
            <div>
              <label className="label">Full name</label>
              <input name="full_name" type="text" value={form.full_name}
                onChange={handle} className="input" placeholder="Ahmed Khan" />
            </div>
            <div>
              <label className="label">Email</label>
              <input name="email" type="email" required value={form.email}
                onChange={handle} className="input" placeholder="you@example.com" />
            </div>
            <div>
              <label className="label">Password</label>
              <input name="password" type="password" required value={form.password}
                onChange={handle} className="input" placeholder="Min. 8 characters" />
              {form.password.length > 0 && (
                <div className="flex gap-1 mt-2">
                  {[1,2,3,4].map(i => (
                    <div key={i} className="h-0.5 flex-1 rounded-full transition-all duration-300" style={{
                      background: form.password.length >= i * 3
                        ? i <= 1 ? '#ef4444' : i <= 2 ? '#f59e0b' : i <= 3 ? '#10b981' : '#10b981'
                        : 'rgba(255,255,255,0.08)'
                    }} />
                  ))}
                </div>
              )}
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full justify-center mt-2">
              {loading
                ? <span className="flex items-center gap-2"><span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />Creating account…</span>
                : <span className="flex items-center gap-2">Create account <ArrowRight size={15} /></span>
              }
            </button>
          </form>

          <div className="flex items-center gap-3 my-6">
            <div className="flex-1 gold-bar" />
            <p className="text-xs text-slate-600">or</p>
            <div className="flex-1 gold-bar" />
          </div>

          <p className="text-center text-sm text-slate-500">
            Already have an account?{' '}
            <Link to="/login" className="text-gold-400 hover:text-gold-300 font-semibold transition-colors">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
