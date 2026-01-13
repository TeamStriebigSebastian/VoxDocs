import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import RecordingPage from './pages/RecordingPage'
import RecordingsListPage from './pages/RecordingsListPage'
import TranscriptionPage from './pages/TranscriptionPage'
import OnboardingPage from './pages/OnboardingPage'
import SettingsPage from './pages/SettingsPage'
import NursingAppointmentPage from './pages/NursingAppointmentPage'
import AppointmentReviewPage from './pages/AppointmentReviewPage'
import AppointmentsListPage from './pages/AppointmentsListPage'
import TranscriptionNotification from './components/TranscriptionNotification'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<RecordingPage />} />
        <Route path="/recordings" element={<RecordingsListPage />} />
        <Route path="/transcription/:uuid" element={<TranscriptionPage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/settings" element={<SettingsPage />} />

        {/* Nursing care appointment routes */}
        <Route path="/appointments" element={<AppointmentsListPage />} />
        <Route path="/nursing/appointment" element={<NursingAppointmentPage />} />
        <Route path="/appointment/:appointmentUuid/review" element={<AppointmentReviewPage />} />
      </Routes>

      {/* Global notification system */}
      <TranscriptionNotification />
    </Layout>
  )
}

export default App
