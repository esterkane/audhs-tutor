import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

for (const width of [390, 1280]) test(`lost recap response cannot erase a newer local draft ${width}`, async ({ page, request }) => {
  await endOpenSession(request)
  try {
    await expectOk(await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } }))
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/')
    await page.getByRole('button', { name: 'Continue', exact: true }).click()
    await page.goto('/recap')
    const notes = page.getByLabel('One line for next time (optional)')
    await notes.fill('Original saved recap')
    let calls = 0
    await page.route('**/api/sessions/*/end', async route => {
      calls++
      if (calls === 1) {
        const saved = await route.fetch()
        await expectOk(saved)
        await route.abort('failed')
      } else await route.continue()
    })
    await page.getByRole('button', { name: 'Save and finish session' }).click()
    await expect(page.getByRole('alert')).toBeVisible()
    await notes.fill('New local notes after lost response')
    await page.getByRole('button', { name: 'Save and finish session' }).click()
    await expect(page.getByRole('alert')).toBeVisible()
    await expect.poll(() => calls).toBe(2)
    await page.waitForTimeout(250) // Let the deliberately retried response settle before inspecting the old error.
    await expect(page.getByRole('button', { name: 'Saving…', exact: true })).not.toBeVisible()
    await expect(page.getByRole('alert')).toBeVisible()
    await expect(notes).toHaveValue('New local notes after lost response')
    await expect(page.getByRole('heading', { name: 'Session saved', exact: true })).not.toBeVisible()
    let failRead = true
    await page.route('**/api/sessions/*/completion', route => failRead
      ? route.fulfill({ status: 503, json: { error: { code: 'unavailable', message: 'Receipt temporarily unavailable' } } })
      : route.continue())
    await page.getByRole('button', { name: 'Check saved recap' }).click()
    await expect(page.getByText(/Could not check the saved recap/)).toBeVisible()
    await expect(notes).toHaveValue('New local notes after lost response')
    failRead = false
    await page.getByRole('button', { name: 'Check saved recap' }).focus()
    await page.keyboard.press('Enter')
    await expect(page.getByLabel('Saved notes', { exact: true })).toHaveValue('Original saved recap')
    await expect(notes).toHaveValue('New local notes after lost response')
    await expect(page.getByRole('button', { name: 'Session already ended' })).toBeDisabled()
    await page.reload()
    await expect(page.getByLabel('Saved notes', { exact: true })).toHaveValue('Original saved recap')
    await expect(notes).toHaveValue('New local notes after lost response')
    expect(calls).toBe(2)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.screenshot({ path: `/tmp/recap-receipt-${width}.png`, fullPage: true })
    await notes.focus()
    await page.keyboard.press('ControlOrMeta+A')
    expect(await notes.evaluate((element: HTMLTextAreaElement) => element.value.slice(element.selectionStart, element.selectionEnd))).toBe('New local notes after lost response')
    await page.getByRole('button', { name: 'Return Home', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL(/\/$/)
    expect(await page.evaluate(() => Object.keys(sessionStorage).some(key => key.startsWith('audhs-recap:v1:') && sessionStorage.getItem(key)?.includes('New local notes after lost response')))).toBe(true)
    expect(calls).toBe(2)
  } finally { await endOpenSession(request) }
})
