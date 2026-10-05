import { expect, test } from '@playwright/test'
import { openMainMenu } from './helpers'

for (const width of [390, 1280]) {
  test(`preferences can be traversed and exited by keyboard at ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    const writes: string[] = []
    page.on('request', request => {
      if (request.url().endsWith('/api/preferences') && request.method() === 'PUT') writes.push(request.postData() ?? '')
    })
    await page.goto('/')
    await openMainMenu(page)
    await page.getByText('Manage', { exact: true }).click()
    const preferences = page.getByRole('link', { name: 'Preferences', exact: true })
    await preferences.focus()
    await page.keyboard.press('Enter')
    const main = page.getByRole('main')
    await expect(main.getByRole('button', { name: 'large', exact: true })).toBeVisible()
    // Anchor this scoped traversal after route loading; entry above uses keyboard activation.
    await main.focus()
    const controls = main.locator('button:visible:not(:disabled), input:visible:not(:disabled), a[href]:visible, summary:visible')
    const count = await controls.count()
    expect(count).toBeGreaterThan(10)
    for (let i = 0; i < count; i++) {
      await page.keyboard.press('Tab')
      const control = controls.nth(i)
      await expect(control).toBeFocused()
      await expect(control).toBeInViewport()
      expect(await control.evaluate(element => {
        const style = getComputedStyle(element)
        return (style.outlineStyle !== 'none' && parseFloat(style.outlineWidth) > 0) || style.boxShadow !== 'none'
      }), `visible focus indicator for control ${i}`).toBe(true)
    }
    // Reverse traversal must return to the first setting without trapping focus.
    for (let i = count - 2; i >= 0; i--) {
      await page.keyboard.press('Shift+Tab')
      await expect(controls.nth(i)).toBeFocused()
    }
    expect(writes).toEqual([])
    await page.screenshot({ path: info.outputPath('keyboard-first-setting.png') })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
    const back = main.getByRole('button', { name: 'Back', exact: true })
    await back.focus()
    await page.keyboard.press('Enter')
    await expect(page).toHaveURL('/')
    await expect(page.getByRole('main')).toBeVisible()
    await info.attach('traversal', { body: `${count} preference/adaptation controls reached in both directions; no writes.`, contentType: 'text/plain' })
  })
}
