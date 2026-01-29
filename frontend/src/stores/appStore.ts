import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface Room {
  id: number
  name: string
}

interface AppState {
  // Practice settings
  practiceId: number
  practiceName: string
  rooms: Room[]
  selectedRoomId: number | null

  // User settings
  userId: number | null
  userName: string | null
  userRole: string | null
  userLanguage: string
  token: string | null

  // Recording settings
  processImmediately: boolean
  pushToTalk: boolean  // PTT mode: hold to record

  // Actions
  setPractice: (id: number, name: string) => void
  setRooms: (rooms: Room[]) => void
  setSelectedRoom: (roomId: number | null) => void
  setUserInfo: (id: number, name: string, role: string, language: string) => void
  setToken: (token: string | null) => void
  logout: () => void
  setProcessImmediately: (value: boolean) => void
  setPushToTalk: (value: boolean) => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // Default values
      practiceId: 1,
      practiceName: 'Zahnarztpraxis Demo',
      rooms: [
        { id: 1, name: 'Behandlungsraum 1' },
        { id: 2, name: 'Behandlungsraum 2' },
        { id: 3, name: 'Behandlungsraum 3' },
      ],
      selectedRoomId: 1,
      userId: null,
      userName: null,
      userRole: null,
      userLanguage: 'de',
      token: null,
      processImmediately: false,
      pushToTalk: false,  // Default: toggle mode (click to start/stop)

      // Actions
      setPractice: (id, name) => set({ practiceId: id, practiceName: name }),
      setRooms: (rooms) => set({ rooms }),
      setSelectedRoom: (roomId) => set({ selectedRoomId: roomId }),
      setUserInfo: (id, name, role, language) => set({
        userId: id,
        userName: name,
        userRole: role,
        userLanguage: language
      }),
      setToken: (token) => set({ token }),
      logout: () => set({
        userId: null,
        userName: null,
        userRole: null,
        token: null
      }),
      setProcessImmediately: (value) => set({ processImmediately: value }),
      setPushToTalk: (value) => set({ pushToTalk: value }),
    }),
    {
      name: 'voxdocs-storage',
    }
  )
)
