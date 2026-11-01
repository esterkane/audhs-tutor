import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { IsolationLab } from './IsolationLab'
import { t } from '../i18n'

beforeEach(() => localStorage.clear())
afterEach(() => { cleanup(); vi.restoreAllMocks() })
for (const language of ['en', 'de'] as const) {
  test(`only explicit submission sends the bounded experiment (${language})`, () => {
    const s = t(language), run = vi.fn()
    render(<IsolationLab s={s} language={language} disabled={false} storageKey="synthetic/A" onRun={run} />)
    fireEvent.change(screen.getByLabelText(s.isolationWorkers), { target: { value: '3' } })
    fireEvent.change(screen.getByLabelText(s.isolationMinimum), { target: { value: '2' } })
    fireEvent.change(screen.getByLabelText(s.isolationFirst), { target: { value: 'b' } })
    expect(run).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: s.isolationRun }))
    expect(run).toHaveBeenCalledExactlyOnceWith(language === 'de'
      ? 'Vergleiche Transaktionsisolation lokal mit 3 aktiven Kräften, mindestens 2, und Commit-Versuch B zuerst.'
      : "Compare transaction isolation locally for 3 active workers, minimum 2, attempting B's commit first.")
  })
}
for (const [workers, minimum] of [['1', '1'], ['21', '1'], ['2', '3'], ['2', '-1'], ['2', ''], ['1e1', '1']]) {
  test(`invalid counts retain the form and never send (${workers}/${minimum})`, () => {
    const s = t('en'), run = vi.fn()
    render(<IsolationLab s={s} language="en" disabled={false} storageKey="synthetic/A" onRun={run} />)
    fireEvent.change(screen.getByLabelText(s.isolationWorkers), { target: { value: workers } })
    fireEvent.change(screen.getByLabelText(s.isolationMinimum), { target: { value: minimum } })
    fireEvent.click(screen.getByRole('button', { name: s.isolationRun }))
    expect(run).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent(s.isolationInvalid)
    expect(screen.getByLabelText(s.isolationMinimum)).toHaveValue(minimum)
  })
}
test('form values resume only in their learner/session namespace', () => {
  const s = t('en'), run = vi.fn()
  const a = render(<IsolationLab s={s} language="en" disabled={false} storageKey="synthetic/A" onRun={run} />)
  fireEvent.change(screen.getByLabelText(s.isolationWorkers), { target: { value: '20' } })
  a.unmount()
  const resumed = render(<IsolationLab s={s} language="en" disabled={false} storageKey="synthetic/A" onRun={run} />)
  expect(screen.getByLabelText(s.isolationWorkers)).toHaveValue('20')
  resumed.unmount()
  render(<IsolationLab s={s} language="en" disabled={false} storageKey="synthetic/B" onRun={run} />)
  expect(screen.getByLabelText(s.isolationWorkers)).toHaveValue('2')
  expect(run).not.toHaveBeenCalled()
})
test('disabled controls cannot send and storage failures keep edits visible', () => {
  const s = t('en'), run = vi.fn()
  const view = render(<IsolationLab s={s} language="en" disabled storageKey="synthetic/A" onRun={run} />)
  expect(screen.getByRole('button', { name: s.isolationRun })).toBeDisabled()
  fireEvent.submit(view.container.querySelector('form')!)
  expect(run).not.toHaveBeenCalled()
  view.rerender(<IsolationLab s={s} language="en" disabled={false} storageKey="synthetic/A" onRun={run} />)
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => { throw new Error('quota') })
  fireEvent.change(screen.getByLabelText(s.isolationWorkers), { target: { value: '4' } })
  expect(screen.getByLabelText(s.isolationWorkers)).toHaveValue('4')
  expect(screen.getByRole('status')).toHaveTextContent(s.draftNotSaved)
})
