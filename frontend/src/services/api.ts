import axios from 'axios'

const API_BASE_URL = '/api'

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Audio API
export const audioApi = {
  upload: async (file: Blob, practiceId: number, roomId?: number, processImmediately = false) => {
    const formData = new FormData()
    formData.append('file', file, 'recording.webm')
    formData.append('practice_id', practiceId.toString())
    if (roomId) {
      formData.append('room_id', roomId.toString())
    }
    formData.append('process_immediately', processImmediately.toString())

    const response = await api.post('/audio/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  get: async (uuid: string) => {
    const response = await api.get(`/audio/${uuid}`)
    return response.data
  },

  list: async (practiceId: number, page = 1, pageSize = 20) => {
    const response = await api.get('/audio/', {
      params: { practice_id: practiceId, page, page_size: pageSize },
    })
    return response.data
  },

  delete: async (uuid: string) => {
    const response = await api.delete(`/audio/${uuid}`)
    return response.data
  },
}

// Transcription API
export const transcriptionApi = {
  get: async (recordingUuid: string) => {
    const response = await api.get(`/transcription/${recordingUuid}`)
    return response.data
  },

  process: async (recordingUuid: string) => {
    const response = await api.post(`/transcription/${recordingUuid}/process`)
    return response.data
  },

  correct: async (recordingUuid: string, correctedText: string, segmentId?: number) => {
    const response = await api.post(`/transcription/${recordingUuid}/correct`, {
      corrected_text: correctedText,
      segment_id: segmentId,
    })
    return response.data
  },

  download: async (recordingUuid: string, format: 'txt' | 'srt' = 'txt') => {
    const response = await api.get(`/transcription/${recordingUuid}/download`, {
      params: { format },
    })
    return response.data
  },
}

// Classification API
export const classificationApi = {
  get: async (recordingUuid: string) => {
    const response = await api.get(`/classification/${recordingUuid}`)
    return response.data
  },

  classifyText: async (text: string) => {
    const response = await api.post('/classification/classify-text', { text })
    return response.data
  },

  verify: async (recordingUuid: string, classificationId: number, userId: number) => {
    const response = await api.post(
      `/classification/${recordingUuid}/${classificationId}/verify`,
      null,
      { params: { user_id: userId } }
    )
    return response.data
  },

  getCategories: async () => {
    const response = await api.get('/classification/categories')
    return response.data
  },
}

// Onboarding API
export const onboardingApi = {
  start: async (practiceId: number, userId: number, speakerName?: string, speakerNotes?: string) => {
    const response = await api.post('/onboarding/start', null, {
      params: {
        practice_id: practiceId,
        user_id: userId,
        speaker_name: speakerName,
        speaker_notes: speakerNotes
      },
    })
    return response.data
  },

  getSession: async (sessionId: number) => {
    const response = await api.get(`/onboarding/${sessionId}`)
    return response.data
  },

  getPhrases: async (sessionId: number) => {
    const response = await api.get(`/onboarding/${sessionId}/phrases`)
    return response.data
  },

  recordPhrase: async (
    sessionId: number,
    file: Blob,
    category: string,
    phraseIndex: number,
    phraseText: string
  ) => {
    const formData = new FormData()
    formData.append('file', file, 'phrase.webm')
    formData.append('category', category)
    formData.append('phrase_index', phraseIndex.toString())
    formData.append('phrase_text', phraseText)

    const response = await api.post(`/onboarding/${sessionId}/record`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  },

  getAllPhrases: async () => {
    const response = await api.get('/onboarding/phrases/all')
    return response.data
  },

  updateSpeaker: async (sessionId: number, speakerName?: string, speakerNotes?: string) => {
    const response = await api.patch(`/onboarding/${sessionId}/speaker`, null, {
      params: { speaker_name: speakerName, speaker_notes: speakerNotes },
    })
    return response.data
  },

  listSessions: async (practiceId?: number) => {
    const response = await api.get('/onboarding/sessions/list', {
      params: practiceId ? { practice_id: practiceId } : {},
    })
    return response.data
  },

  exportSession: (sessionId: number) => {
    // Return URL for direct download
    return `${api.defaults.baseURL}/onboarding/${sessionId}/export`
  },

  exportAll: (practiceId?: number) => {
    // Return URL for direct download
    const params = practiceId ? `?practice_id=${practiceId}` : ''
    return `${api.defaults.baseURL}/onboarding/export/all${params}`
  },
}

// Export API
export const exportApi = {
  generate: async (practiceId: number, format: 'json' | 'csv' | 'xml', startDate?: string, endDate?: string) => {
    const response = await api.post('/export/generate', {
      practice_id: practiceId,
      format,
      start_date: startDate,
      end_date: endDate,
    })
    return response.data
  },

  getFormats: async () => {
    const response = await api.get('/export/formats')
    return response.data
  },
}

// Health API
export const healthApi = {
  check: async () => {
    const response = await api.get('/health')
    return response.data
  },

  detailed: async () => {
    const response = await api.get('/health/detailed')
    return response.data
  },
}

export default api
