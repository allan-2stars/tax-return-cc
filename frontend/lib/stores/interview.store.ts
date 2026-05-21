import { create } from 'zustand'

interface InterviewStore {
  newSkillPending: string | null
  setNewSkillPending: (skillId: string | null) => void
}

const useInterviewStore = create<InterviewStore>((set) => ({
  newSkillPending: null,
  setNewSkillPending: (skillId) => set({ newSkillPending: skillId }),
}))

export default useInterviewStore
