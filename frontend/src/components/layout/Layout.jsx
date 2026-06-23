import { Outlet, NavLink, useNavigate, useLocation } from 'react-router-dom'
import { MessageSquare, ListChecks, Bell, ScanLine, LogOut, Stamp } from 'lucide-react'
import { useAuth } from '../../context/AuthContext'
import clsx from 'clsx'

const NAV = [
  { to: '/chat',      icon: MessageSquare, label: 'Q&A Assistant',  sub: 'Ask visa questions'   },
  { to: '/checklist', icon: ListChecks,    label: 'Checklists',     sub: 'Document tracker'      },
  { to: '/alerts',    icon: Bell,          label: 'Policy Alerts',  sub: 'Live changes'          },
  { to: '/scanner',   icon: ScanLine,      label: 'Doc Scanner',    sub: 'Extract & autofill'    },
]

// Animated passport stamp logo
function Logo() {
  return (
    <div className="relative w-10 h-10 flex items-center justify-center">
      {/* spinning ring */}
      <div className="absolute inset-0 rounded-full border border-dashed border-gold-500/30 animate-spin-slow" />
      {/* glow */}
      <div className="absolute inset-1 rounded-full bg-gold-500/8 animate-glow-pulse" />
      {/* icon */}
      <Stamp size={18} className="text-gold-400 relative z-10" />
    </div>
  )
}

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = () => { logout(); navigate('/login') }

  // Get initials
  const initials = user?.full_name
    ? user.full_name.split(' ').map(w => w[0]).join('').slice(0,2).toUpperCase()
    : user?.email?.[0]?.toUpperCase() ?? 'U'

  return (
    <div className="flex min-h-screen">
      {/* ── Sidebar ── */}
      <aside className="w-[240px] shrink-0 flex flex-col relative" style={{
        background: 'rgba(5,8,15,0.95)',
        borderRight: '1px solid rgba(180,140,60,0.1)',
        backdropFilter: 'blur(20px)',
      }}>
        {/* Ambient glow top */}
        <div className="absolute top-0 left-0 right-0 h-48 pointer-events-none" style={{
          background: 'radial-gradient(ellipse at 50% 0%, rgba(180,140,60,0.08) 0%, transparent 70%)',
        }} />

        {/* Logo */}
        <div className="px-5 py-6 relative">
          <div className="flex items-center gap-3">
            <Logo />
            <div>
              <p className="text-white font-display font-semibold text-lg leading-tight tracking-wide">PassportAI</p>
              <p className="text-[10px] uppercase tracking-[0.2em]" style={{ color: 'rgba(180,140,60,0.6)' }}>Visa Intelligence</p>
            </div>
          </div>
          <div className="mt-4 gold-bar" />
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-2 space-y-1">
          {NAV.map(({ to, icon: Icon, label, sub }, idx) => (
            <NavLink
              key={to}
              to={to}
              style={{ animationDelay: `${idx * 60}ms` }}
              className={({ isActive }) => clsx(
                'group flex items-center gap-3 px-3 py-3 rounded-xl transition-all duration-200 animate-slide-left relative overflow-hidden',
                isActive
                  ? 'text-gold-400'
                  : 'text-slate-500 hover:text-slate-200'
              )}
            >
              {({ isActive }) => (
                <>
                  {/* Active background */}
                  {isActive && (
                    <div className="absolute inset-0 rounded-xl" style={{
                      background: 'linear-gradient(135deg, rgba(180,140,60,0.12), rgba(180,140,60,0.04))',
                      border: '1px solid rgba(180,140,60,0.18)',
                    }} />
                  )}
                  {/* Hover background */}
                  {!isActive && (
                    <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-200" style={{
                      background: 'rgba(255,255,255,0.03)',
                    }} />
                  )}

                  {/* Icon container */}
                  <div className={clsx(
                    'relative z-10 w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-200 shrink-0',
                    isActive
                      ? 'bg-gold-500/15'
                      : 'bg-white/3 group-hover:bg-white/6'
                  )}>
                    <Icon size={15} />
                  </div>

                  {/* Labels */}
                  <div className="relative z-10 min-w-0">
                    <p className={clsx('text-sm font-semibold leading-tight', isActive ? 'text-gold-400' : 'text-slate-300 group-hover:text-white')} style={{ fontFamily: 'Syne' }}>
                      {label}
                    </p>
                    <p className="text-[10px] mt-0.5 truncate" style={{ color: isActive ? 'rgba(180,140,60,0.6)' : 'rgba(148,163,184,0.5)' }}>
                      {sub}
                    </p>
                  </div>

                  {/* Active indicator */}
                  {isActive && (
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 w-1 h-4 rounded-full bg-gold-400" />
                  )}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Divider */}
        <div className="mx-5 gold-bar" />

        {/* User section */}
        <div className="p-3 mt-2 mb-2">
          <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl mb-1" style={{
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.05)',
          }}>
            <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-gold-400 shrink-0" style={{
              background: 'rgba(180,140,60,0.12)',
              border: '1px solid rgba(180,140,60,0.2)',
              fontFamily: 'Syne',
            }}>
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold text-slate-300 truncate">{user?.full_name || 'User'}</p>
              <p className="text-[10px] text-slate-600 truncate">{user?.email}</p>
            </div>
          </div>

          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm text-slate-500 hover:text-red-400 transition-all duration-200 group"
            style={{ fontFamily: 'Syne' }}
          >
            <div className="w-8 h-8 rounded-lg flex items-center justify-center group-hover:bg-red-500/10 transition-colors">
              <LogOut size={14} />
            </div>
            Sign out
          </button>
        </div>
      </aside>

      {/* ── Main ── */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
