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
  userName: string

  // Recording settings
  processImmediately: boolean

  // Actions
  setPractice: (id: number, name: string) => void
  setRooms: (rooms: Room[]) => void
  setSelectedRoom: (roomId: number | null) => void
  setUser: (id: number, name: string) => void
  setProcessImmediately: (value: boolean) => void
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
      userId: 1,
      userName: 'Dr. Demo',
      processImmediately: false,

      // Actions
      setPractice: (id, name) => set({ practiceId: id, practiceName: name }),
      setRooms: (rooms) => set({ rooms }),
      setSelectedRoom: (roomId) => set({ selectedRoomId: roomId }),
      setUser: (id, name) => set({ userId: id, userName: name }),
      setProcessImmediately: (value) => set({ processImmediately: value }),
    }),
    {
      name: 'voxdocs-storage',
    }
  )
)
