import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { DeliveryChooser } from './TutorApp'
import { t } from './i18n'

for (const language of ['en', 'de'] as const) {
  describe(`session choice (${language})`, () => {
    const strings = t(language)
    for (const [label, delivery, mode] of [
      [strings.deliveryExplicit, 'explicit', 'lesson'],
      [strings.deliverySocratic, 'socratic', 'lesson'],
      [strings.deliveryDiscussion, 'explicit', 'neutral'],
    ]) {
      it(`chooses ${mode} only after the learner selects ${label}`, () => {
        const choose = vi.fn()
        render(<DeliveryChooser s={strings} onChoose={choose} />)
        expect(choose).not.toHaveBeenCalled()
        fireEvent.click(screen.getByText(label, { exact: true }))
        expect(choose).toHaveBeenCalledExactlyOnceWith(delivery, mode)
      })
    }
    it('cancel leaves the existing session choice unchanged', () => {
      const choose = vi.fn(), cancel = vi.fn()
      render(<DeliveryChooser s={strings} onChoose={choose} onCancel={cancel} />)
      fireEvent.click(screen.getByRole('button', { name: strings.cancel }))
      expect(cancel).toHaveBeenCalledOnce()
      expect(choose).not.toHaveBeenCalled()
    })
  })
}
