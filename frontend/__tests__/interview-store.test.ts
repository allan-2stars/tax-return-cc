import { act, renderHook } from '@testing-library/react'
import useInterviewStore from '@/lib/stores/interview.store'

beforeEach(() => {
  useInterviewStore.setState({ newSkillPending: null })
})

test('newSkillPending starts null', () => {
  const { result } = renderHook(() => useInterviewStore())
  expect(result.current.newSkillPending).toBeNull()
})

test('setNewSkillPending updates skill id', () => {
  const { result } = renderHook(() => useInterviewStore())
  act(() => result.current.setNewSkillPending('wfh_skill'))
  expect(result.current.newSkillPending).toBe('wfh_skill')
})

test('setNewSkillPending can clear to null', () => {
  const { result } = renderHook(() => useInterviewStore())
  act(() => result.current.setNewSkillPending('wfh_skill'))
  act(() => result.current.setNewSkillPending(null))
  expect(result.current.newSkillPending).toBeNull()
})
