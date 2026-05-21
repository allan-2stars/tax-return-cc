import { create } from 'zustand'

interface InterviewStore {
  sessionId: string | null
  setSessionId: (id: string | null) => void
  newSkillPending: string | null
  setNewSkillPending: (skillId: string | null) => void
}

const useInterviewStore = create<InterviewStore>((set) => ({
  sessionId: null,
  setSessionId: (id) => set({ sessionId: id }),
  newSkillPending: null,
  setNewSkillPending: (skillId) => set({ newSkillPending: skillId }),
}))

export default useInterviewStore
