import { fireEvent, render, screen, cleanup } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { MembershipLab } from './MembershipLab'
import { t } from '../i18n'

beforeEach(() => localStorage.clear())
afterEach(() => { cleanup(); vi.restoreAllMocks() })
for (const language of ['en', 'de'] as const) {
  test(`valid literal values require explicit submission (${language})`, () => {
    const compare = vi.fn(), s = t(language)
    render(<MembershipLab s={s} language={language} disabled={false} storageKey="lab/A" onCompare={compare} />)
    expect(compare).not.toHaveBeenCalled()
    fireEvent.change(screen.getByLabelText(s.membershipOuter), { target: { value: 'null' } })
    fireEvent.change(screen.getByLabelText(s.membershipInner), { target: { value: '[]' } })
    fireEvent.click(screen.getByRole('button', { name: s.membershipRun }))
    expect(compare).toHaveBeenCalledOnce()
    expect(compare.mock.calls[0][0]).toContain(language === 'en' ? 'outer value null and inner values []' : 'äußeren Wert null und die inneren Werte []')
  })
}
for (const invalid of ['[true]', '["DROP TABLE users"]', '[1.2]', JSON.stringify(Array(21).fill(1))]) {
  test(`invalid values do not send: ${invalid}`, () => {
    const compare = vi.fn(), s = t('en')
    render(<MembershipLab s={s} language="en" disabled={false} onCompare={compare} />)
    fireEvent.change(screen.getByLabelText(s.membershipInner), { target: { value: invalid } })
    fireEvent.click(screen.getByRole('button', { name: s.membershipRun }))
    expect(compare).not.toHaveBeenCalled()
    expect(screen.getByRole('alert')).toHaveTextContent('at most 20')
    expect(screen.getByLabelText(s.membershipInner)).toHaveValue(invalid)
  })
}
test('edited values resume only in their learner/session namespace', () => {
  const s = t('en'), compare = vi.fn()
  const view = render(<MembershipLab s={s} language="en" disabled={false} storageKey="lab/A" onCompare={compare} />)
  fireEvent.change(screen.getByLabelText(s.membershipOuter), { target: { value: '42' } })
  view.unmount()
  const same = render(<MembershipLab s={s} language="en" disabled={false} storageKey="lab/A" onCompare={compare} />)
  expect(screen.getByLabelText(s.membershipOuter)).toHaveValue('42')
  same.unmount()
  render(<MembershipLab s={s} language="en" disabled={false} storageKey="lab/B" onCompare={compare} />)
  expect(screen.getByLabelText(s.membershipOuter)).toHaveValue('2')
  expect(compare).not.toHaveBeenCalled()
})
