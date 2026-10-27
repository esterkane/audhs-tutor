import { expect, test } from '@playwright/test'
import axe from 'axe-core'

for (const width of [1280, 390, 320]) test(`six destinations and grouped pages preserve orientation ${width}`, async ({ page }, info) => {
  await page.setViewportSize({ width, height: 900 })
  await page.goto('/practice')
  const nav = page.getByRole('navigation', { name: 'Main navigation', exact: true })
  await expect(nav.getByRole('link')).toHaveCount(6)
  for (const name of ['Home', 'Library', 'Progress', 'Projects', 'Ask', 'Settings']) await expect(nav.getByRole('link', { name, exact: true })).toBeVisible()
  await expect(nav.getByRole('link', { name: 'Home', exact: true })).toHaveAttribute('aria-current', 'page')
  if (width < 768) {
    const box = await nav.boundingBox()
    expect(box!.y + box!.height).toBeCloseTo(900, 0)
  } else {
    await page.getByRole('button', { name: 'Collapse navigation' }).click()
    await expect(nav.getByRole('link', { name: 'Library' })).toBeVisible()
    await page.getByRole('button', { name: 'Expand navigation' }).focus()
    await page.setViewportSize({ width: 390, height: 900 })
    await expect(nav.getByRole('link', { name: 'Home', exact: true })).toBeFocused()
    await page.setViewportSize({ width, height: 900 })
    await page.getByRole('button', { name: 'Expand navigation' }).click()
  }
  await page.getByRole('link', { name: 'Skip to learning content' }).focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('main')).toBeFocused()
  const ask = page.getByRole('link', { name: 'Ask', exact: true })
  await expect(ask).toBeVisible()
  await ask.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'Ask the tutor', exact: true })).toBeVisible()
  await expect(ask).toHaveAttribute('aria-current', 'page')
  await expect(page.getByRole('textbox', { name: 'Your question', exact: true })).toBeVisible()
  await page.screenshot({ path: info.outputPath('ask-navigation.png'), fullPage: true })
  await page.goBack()
  await expect(page).toHaveTitle('Practice · AuDHS Tutor')
  await nav.getByRole('link', {name:'Library', exact:true}).click()
  await expect(page).toHaveTitle('Library · AuDHS Tutor')
  await page.getByRole('link',{name:'Create or continue knowledge material',exact:true}).click()
  await expect(page).toHaveTitle('Knowledge material · AuDHS Tutor')
  await expect(nav.getByRole('link',{name:'Library',exact:true})).toHaveAttribute('aria-current','page')
  await expect(page.getByRole('main')).toBeFocused()
  await page.goBack()
  await expect(page).toHaveTitle('Library · AuDHS Tutor')
  await page.goForward()
  await expect(page).toHaveTitle('Knowledge material · AuDHS Tutor')
  await page.screenshot({ path: info.outputPath('navigation-normal.png'), fullPage: true })
  await page.evaluate(() => { document.documentElement.style.fontSize = '200%' })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
  if (width < 768) {
    await expect.poll(async () => page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--shell-bottom-nav-height')))).toBeGreaterThan(0)
    const labels = page.locator('.shell-primary-link .shell-primary-label, .shell-preferences-link .shell-primary-label')
    for (const label of await labels.all()) {
      const singleLine = await label.evaluate(el => {
        const range = document.createRange()
        range.selectNodeContents(el)
        return range.getClientRects().length === 1
      })
      expect(singleLine).toBe(true)
    }
    const navBox = (await nav.boundingBox())!
    expect(await page.getByRole('main').evaluate(el => parseFloat(getComputedStyle(el).paddingBottom))).toBeGreaterThanOrEqual(navBox.height)
    const links = nav.getByRole('link')
    await links.first().focus()
    for (let i = 0; i < 6; i++) {
      await expect(links.nth(i)).toBeFocused()
      const box = (await links.nth(i).boundingBox())!
      expect(box.width).toBeGreaterThanOrEqual(44)
      expect(box.height).toBeGreaterThanOrEqual(44)
      expect(box.x).toBeGreaterThanOrEqual(0)
      expect(box.x + box.width).toBeLessThanOrEqual(width)
      if (i < 5) await page.keyboard.press('Tab')
    }
    await page.screenshot({ path: info.outputPath('navigation-large-text.png') })
    if (width === 320) {
      await page.setViewportSize({ width, height: 568 })
      const title = page.getByRole('main').getByRole('heading', { level: 1 })
      await title.evaluate(el => el.scrollIntoView({ block: 'end' }))
      const titleBox = (await title.boundingBox())!
      expect(titleBox.y + titleBox.height).toBeLessThanOrEqual((await nav.boundingBox())!.y)
      await page.screenshot({ path: info.outputPath('navigation-short-large-text.png') })
      await page.setViewportSize({ width, height: 900 })
    }
    await page.evaluate(() => { document.documentElement.style.fontSize = '' })
    await expect.poll(async () => (await nav.boundingBox())!.height).toBeLessThan(navBox.height)
  }

  await page.addScriptTag({ content: axe.source })
  const violations = await page.evaluate(async () => (await (window as unknown as { axe: typeof axe }).axe.run('header, nav', {
    runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] },
  })).violations)
  expect(violations.map(v => v.id)).toEqual([])
})
