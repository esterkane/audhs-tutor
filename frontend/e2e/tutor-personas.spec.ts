import { expect, test } from '@playwright/test'
import axe from 'axe-core'
import { API, expectOk } from './helpers'

for (const width of [1280, 390]) {
  test(`optional persona and language survive navigation without changing teaching mode at ${width}`, async ({ page, request }) => {
    const before = await (await request.get(`${API}/api/preferences`)).json()
    const originalPersona = before.values['tutor.persona']
    const originalLanguage = before.values['tutor.response_language']
    try {
      await expectOk(await request.put(`${API}/api/preferences`, { data: { key: 'tutor.persona', value: 'none' } }))
      await expectOk(await request.put(`${API}/api/preferences`, { data: { key: 'tutor.response_language', value: 'unchanged' } }))
      await page.setViewportSize({ width, height: 900 })
      await page.goto('/preferences')
      await expect(page.getByRole('button', { name: 'No persona', exact: true })).toHaveAttribute('aria-pressed', 'true')
      const kangaroo = page.getByRole('button', { name: 'Känguru / Kangaroo', exact: true })
      await kangaroo.focus()
      await page.keyboard.press('Enter')
      await expect(kangaroo).toHaveAttribute('aria-pressed', 'true')
      await page.getByRole('button', { name: 'English', exact: true }).click()
      await expect(page.getByRole('button', { name: 'English', exact: true })).toHaveAttribute('aria-pressed', 'true')
      await page.reload()
      await expect(kangaroo).toHaveAttribute('aria-pressed', 'true')
      await expect(page.getByRole('button', { name: 'English', exact: true })).toHaveAttribute('aria-pressed', 'true')
      await page.goto('/ask')
      await expect(page.getByLabel('How should the tutor respond?')).toHaveValue('explicit')
      await page.goto('/curriculum')
      await expect(page.getByRole('heading', { name: 'Knowledge material', exact: true, level: 1 })).toBeVisible()
      await page.goto('/preferences')
      await page.getByRole('button', { name: 'Deutsch', exact: true }).click()
      await expect(page.getByRole('button', { name: 'Deutsch', exact: true })).toHaveAttribute('aria-pressed', 'true')
      await page.getByRole('button', { name: 'Calm guide', exact: true }).click()
      await expect(page.getByRole('button', { name: 'Calm guide', exact: true })).toHaveAttribute('aria-pressed', 'true')
      await page.getByRole('button', { name: 'Technical coach', exact: true }).click()
      await expect(page.getByRole('button', { name: 'Technical coach', exact: true })).toHaveAttribute('aria-pressed', 'true')
      await page.getByRole('button', { name: 'No persona', exact: true }).click()
      await expect(page.getByRole('button', { name: 'No persona', exact: true })).toHaveAttribute('aria-pressed', 'true')
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
      await page.addScriptTag({ content: axe.source })
      expect(await page.evaluate(async () => (await (window as unknown as { axe: typeof axe }).axe.run('main')).violations)).toEqual([])
      await page.screenshot({ path: `/tmp/audhs-personas-${width}.png`, fullPage: true })
    } finally {
      await request.put(`${API}/api/preferences`, { data: { key: 'tutor.persona', value: originalPersona } })
      await request.put(`${API}/api/preferences`, { data: { key: 'tutor.response_language', value: originalLanguage } })
    }
  })
}
