import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { AuthProvider, useAuth } from './context/AuthContext'

import Layout from './components/layout/Layout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import ChatPage from './pages/ChatPage'
import ChecklistPage from './pages/ChecklistPage'
import AlertsPage from './pages/AlertsPage'
import ScannerPage from './pages/ScannerPage'

function Spinner() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="relative w-12 h-12">
        <div className="absolute inset-0 rounded-full border-2 border-dashed animate-spin-slow" style={{ borderColor: 'rgba(180,140,60,0.2)' }} />
        <div className="absolute inset-1 rounded-full border-t-2 animate-spin" style={{ borderColor: '#c9a227', borderRightColor: 'transparent', borderBottomColor: 'transparent', borderLeftColor: 'transparent' }} />
      </div>
    </div>
  )
}

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <Spinner />
  return user ? children : <Navigate to="/login" replace />
}

function PublicRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return null
  return user ? <Navigate to="/chat" replace /> : children
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Toaster
          position="top-right"
          toastOptions={{
            style: {
              background: 'rgba(12,18,32,0.95)',
              color: '#e2e8f0',
              border: '1px solid rgba(180,140,60,0.18)',
              fontFamily: '"Syne", sans-serif',
              fontSize: '13px',
              borderRadius: '12px',
              backdropFilter: 'blur(20px)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
            },
            success: { iconTheme: { primary: '#c9a227', secondary: '#05080f' } },
            error: { iconTheme: { primary: '#ef4444', secondary: '#05080f' } },
          }}
        />
        <Routes>
          <Route path="/login"    element={<PublicRoute><LoginPage /></PublicRoute>} />
          <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />
          <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
            <Route index element={<Navigate to="/chat" replace />} />
            <Route path="chat"      element={<ChatPage />} />
            <Route path="checklist" element={<ChecklistPage />} />
            <Route path="alerts"    element={<AlertsPage />} />
            <Route path="scanner"   element={<ScannerPage />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
