import { create } from 'zustand'

interface InterviewStore {
  sessionId: string | null
  setSessionId: (id: string | null) => void
}

const useInterviewStore = create<InterviewStore>((set) => ({
  sessionId: null,
  setSessionId: (id) => set({ sessionId: id }),
}))

export default useInterviewStore
