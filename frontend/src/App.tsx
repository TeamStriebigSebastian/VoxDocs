import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import RecordingPage from './pages/RecordingPage'
import RecordingsListPage from './pages/RecordingsListPage'
import TranscriptionPage from './pages/TranscriptionPage'
import OnboardingPage from './pages/OnboardingPage'
import SettingsPage from './pages/SettingsPage'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<RecordingPage />} />
        <Route path="/recordings" element={<RecordingsListPage />} />
        <Route path="/transcription/:uuid" element={<TranscriptionPage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  )
}

export default App
