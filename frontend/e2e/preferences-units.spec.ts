import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`preference units and keyboard retention save at ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/preferences')
    const retention = page.getByRole('slider', { name: 'Voice: days to keep recordings when retention is on', exact: true })
    const retentionValue = Number(await retention.inputValue())
    await expect(retention).toHaveAttribute('aria-valuetext', `${retentionValue} days`)
    await expect(retention.locator('..')).toContainText(`${retentionValue} days`)
    const newMaterial = page.getByRole('slider', { name: 'Planned minutes for new material', exact: true })
    await expect(newMaterial).toHaveAttribute('aria-valuetext', `${await newMaterial.inputValue()} min`)
    const review = page.getByRole('slider', { name: 'Planned minutes for interleaved review', exact: true })
    await expect(review).toHaveAttribute('aria-valuetext', `${await review.inputValue()} min`)
    await retention.focus()
    const saved = page.waitForResponse(response => response.url().endsWith('/api/preferences') && response.request().method() === 'PUT')
    await page.keyboard.press('ArrowRight')
    const response = await saved
    expect(response.ok()).toBe(true)
    expect(response.request().postDataJSON()).toEqual({ key: 'voice.retention_days', value: retentionValue + 1 })
    await expect(retention).toHaveAttribute('aria-valuetext', `${retentionValue + 1} days`)
    await page.screenshot({ path: info.outputPath('retention-days.png') })
    await page.reload()
    await expect(retention).toHaveValue(String(retentionValue + 1))
    await expect(retention).toHaveAttribute('aria-valuetext', `${retentionValue + 1} days`)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
  })
}
