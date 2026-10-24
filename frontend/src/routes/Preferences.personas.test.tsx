import { fireEvent, screen } from '@testing-library/react'
import { expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { renderApp } from '../test/utils'
import { Preferences } from './Preferences'

const state = vi.hoisted(() => ({ mutate: vi.fn() }))
vi.mock('../features/preferences/api', () => ({
  usePreferences: () => ({ data: {
    values: { 'tutor.persona': 'none', 'tutor.response_language': 'unchanged' },
    specs: [
      { key: 'tutor.persona', type: 'enum', default: 'none', choices: ['none', 'kangaroo', 'guide', 'coach'], description: 'Optional tutor persona (all courses)' },
      { key: 'tutor.response_language', type: 'enum', default: 'unchanged', choices: ['unchanged', 'en', 'de'], description: 'Tutor response language (all courses)' },
    ],
  } }),
  useSetPreference: () => ({ mutate: state.mutate, isPending: false }),
}))
vi.mock('../features/questions/CorrectionInbox', () => ({ CorrectionInbox: () => null }))
vi.mock('../features/questions/QuestionPractice', () => ({ ExcludedQuestions: () => null }))
vi.mock('../features/adaptations/AdaptationCards', () => ({ AdaptationLog: () => null }))

it('keeps personas optional and separates English/German from the teaching mode', async () => {
  const { container } = renderApp(<Preferences />)
  expect(screen.getByRole('button', { name: 'No persona' })).toHaveAttribute('aria-pressed', 'true')
  expect(screen.getByRole('button', { name: 'Follow the conversation' })).toHaveAttribute('aria-pressed', 'true')
  expect(state.mutate).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Känguru / Kangaroo' }))
  expect(state.mutate).toHaveBeenLastCalledWith({ key: 'tutor.persona', value: 'kangaroo' })
  fireEvent.click(screen.getByRole('button', { name: 'English' }))
  expect(state.mutate).toHaveBeenLastCalledWith({ key: 'tutor.response_language', value: 'en' })
  fireEvent.click(screen.getByRole('button', { name: 'Deutsch' }))
  expect(state.mutate).toHaveBeenLastCalledWith({ key: 'tutor.response_language', value: 'de' })
  expect(await axe(container)).toHaveNoViolations()
})
