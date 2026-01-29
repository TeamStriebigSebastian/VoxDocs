import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import RecordingPage from './pages/RecordingPage'
import RecordingsListPage from './pages/RecordingsListPage'
import TranscriptionPage from './pages/TranscriptionPage'
import OnboardingPage from './pages/OnboardingPage'
import SettingsPage from './pages/SettingsPage'
import NursingAppointmentPage from './pages/NursingAppointmentPage'
import AppointmentReviewPage from './pages/AppointmentReviewPage'
import AppointmentsListPage from './pages/AppointmentsListPage'
import CasesListPage from './pages/CasesListPage'
import CaseDetailPage from './pages/CaseDetailPage'
import AdminPage from './pages/AdminPage'
import { LoginPage } from './pages/LoginPage'
import TranscriptionNotification from './components/TranscriptionNotification'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { Loader2 } from 'lucide-react'

// Auth Guard Component
function RequireAuth({ children }: { children: JSX.Element }) {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return children
}

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />

        {/* Protected Routes */}
        <Route path="/*" element={
          <RequireAuth>
            <Layout>
              <Routes>
                {/* Homepage with selection between dental and nursing care */}
                <Route path="/" element={<HomePage />} />

                {/* Dental documentation routes */}
                <Route path="/dental" element={<RecordingPage />} />
                <Route path="/recordings" element={<RecordingsListPage />} />
                <Route path="/transcription/:uuid" element={<TranscriptionPage />} />
                <Route path="/onboarding" element={<OnboardingPage />} />
                <Route path="/settings" element={<SettingsPage />} />

                {/* Nursing care appointment routes */}
                <Route path="/appointments" element={<AppointmentsListPage />} />
                <Route path="/nursing/appointment" element={<NursingAppointmentPage />} />
                <Route path="/appointment/:appointmentUuid/review" element={<AppointmentReviewPage />} />

                {/* Generic Platform routes */}
                <Route path="/platform/cases" element={<CasesListPage />} />
                <Route path="/platform/cases/:uuid" element={<CaseDetailPage />} />
                <Route path="/platform/admin" element={<AdminPage />} />
              </Routes>

              {/* Global notification system */}
              <TranscriptionNotification />
            </Layout>
          </RequireAuth>
        } />
      </Routes>
    </AuthProvider>
  )
}

export default App
