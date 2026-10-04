import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`companion target and drafts survive explicit edits and navigation ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    const writes: string[] = []
    page.on('request', request => { if (request.method() !== 'GET' && request.url().includes('/api/')) writes.push(request.url()) })
    await page.route('**/api/sessions/current', route => route.fulfill({ json: { id: 'fixture-session' } }))
    await page.goto('/sources')
    const open = page.getByRole('button', { name: /Listen or ask about this page|Reopen learning companion/ })
    await open.click()
    const question = page.getByRole('textbox', { name: 'Your tutor message or response' })
    const material = page.getByRole('textbox', { name: 'Material to discuss' })
    await question.fill('Explain why this source matters')
    await material.fill('A different passage')
    await expect(question).toHaveValue('Explain why this source matters')
    await page.getByRole('button', { name: 'Apply material' }).click()
    await expect(question).toHaveValue('')
    await question.fill('Question for the new material')
    await page.getByRole('button', { name: 'Return to previous material' }).click()
    await expect(question).toHaveValue('Explain why this source matters')
    await expect(material).not.toHaveValue('A different passage')
    if (width < 1024) await page.getByRole('button', { name: 'Close learning companion' }).click()
    await page.getByRole('link', { name: 'Search saved tutor answers', exact: true }).click()
    if (width < 1024) await open.click()
    await expect(question).toHaveValue('Explain why this source matters')
    await expect(page.getByText(/You are browsing another page/)).toBeVisible()
    if (width < 1024) {
      await page.getByRole('dialog').getByRole('link', { name: 'Sources', exact: true }).click()
      await expect(page.getByRole('dialog')).not.toBeVisible()
      await expect(page.locator('main')).toBeFocused()
      await open.click()
    } else await page.goBack()
    await expect(question).toHaveValue('Explain why this source matters')
    await material.fill('Unapplied draft survives reload')
    await page.reload()
    await open.click()
    await expect(material).toHaveValue('Unapplied draft survives reload')
    await expect(question).toHaveValue('Explain why this source matters')
    await page.getByRole('button', { name: 'Discard material edits' }).click()
    await page.getByRole('button', { name: 'Close learning companion' }).focus()
    await page.keyboard.press('Enter')
    await expect(open).toBeFocused()
    await page.keyboard.press('Enter')
    await expect(question).toHaveValue('Explain why this source matters')
    await page.screenshot({ path: info.outputPath('retained-context.png'), fullPage: true })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.addStyleTag({ content: 'html { font-size: 200% !important; }' })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    expect(writes).toEqual([])
  })
}

test('companion discloses unavailable storage and preserves in-memory material', async ({ page }) => {
  await page.addInitScript(() => {
    const original = Storage.prototype.setItem
    Storage.prototype.setItem = function(key, value) {
      if (key === 'learning-companion:context:v1') throw new Error('Fixture storage blocked')
      return original.call(this, key, value)
    }
  })
  await page.goto('/sources')
  await page.getByRole('button', { name: /Listen or ask about this page|Reopen learning companion/ }).click()
  const material = page.getByRole('textbox', { name: 'Material to discuss' })
  await material.fill('Keep this draft')
  await expect(page.getByText(/Captured material could not be saved/)).toBeVisible()
  await page.getByRole('button', { name: 'Close learning companion' }).click()
  await page.getByRole('button', { name: /Listen or ask about this page|Reopen learning companion/ }).click()
  await expect(material).toHaveValue('Keep this draft')
})

test('closing a pending companion preserves exact request recovery', async ({ page }) => {
  await page.route('**/api/sessions/current', route => route.fulfill({ json: { id: 'fixture-session' } }))
  const calls: { key: string | undefined; body: unknown }[] = []
  let release!: () => void, start!: () => void, finish!: () => void
  const pending = new Promise<void>(resolve => { release = resolve })
  const started = new Promise<void>(resolve => { start = resolve })
  const delivered = new Promise<void>(resolve => { finish = resolve })
  await page.route('**/api/playground/tutor', async route => {
    calls.push({ key: route.request().headers()['idempotency-key'], body: route.request().postDataJSON() })
    if (calls.length === 1) { start(); await pending }
    await route.fulfill({ json: { text: 'Recovered original reply', model: 'fixture', route: 'local', turn_id: 'fixture-turn', source_note: 'Fixture only' } })
    finish()
  })
  await page.goto('/sources')
  const open = page.getByRole('button', { name: /Listen or ask about this page|Reopen learning companion/ })
  await open.click()
  const question = page.getByRole('textbox', { name: 'Your tutor message or response' })
  await question.fill('Keep this request')
  await page.getByRole('button', { name: 'Send to tutor', exact: true }).click()
  await started
  await page.getByRole('button', { name: 'Close learning companion' }).click()
  release()
  await delivered
  await open.click()
  await expect(question).toHaveValue('Keep this request')
  await expect(page.getByText('Recovered original reply', { exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: 'Retry previous request' }).click()
  await expect(page.getByText('Recovered original reply', { exact: true }).first()).toBeVisible()
  expect(calls).toHaveLength(2)
  expect(calls[1]).toEqual(calls[0])
})

test('invalid companion checkpoint is disclosed without opening an unsafe return link', async ({ page }) => {
  await page.addInitScript(() => {
    const capture = { id: '00000000-0000-0000-0000-000000000000', text: 'Saved', title: 'Unsafe', path: '//example.invalid' }
    sessionStorage.setItem('learning-companion:context:v1', JSON.stringify({ version: 1, active: capture, draft: capture, previous: null }))
  })
  await page.goto('/sources')
  await expect(page.getByText(/Captured material could not be restored/)).toBeVisible()
  await expect(page.getByRole('link', { name: 'Unsafe', exact: true })).toHaveCount(0)
  expect(await page.evaluate(() => sessionStorage.getItem('learning-companion:context:v1'))).toContain('example.invalid')
  await page.getByRole('button', { name: 'Listen or ask about this page' }).click()
  await expect(page.getByText(/Captured material could not be restored/)).toHaveCount(0)
})


test('tutor keeps one pending conversation across desktop and sheet resizing', async ({ page }, info) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.route('**/api/sessions/current', route => route.fulfill({ json: { id: 'fixture-session' } }))
  let release!: () => void
  const pending = new Promise<void>(resolve => { release = resolve })
  let calls = 0
  await page.route('**/api/playground/tutor', async route => {
    calls++
    await pending
    await route.fulfill({ json: { text: 'Reply after resize', model: 'fixture', route: 'local', turn_id: 'resize-turn', source_note: 'Fixture only' } })
  })
  await page.goto('/sources')
  const open = page.getByRole('button', { name: /Listen or ask about this page|Reopen learning companion/ })
  await open.click()
  const panel = page.getByRole('dialog', { name: 'Learning companion' })
  const question = page.getByRole('textbox', { name: 'Your tutor message or response' })
  await question.fill('Retain this conversation')
  await page.getByRole('button', { name: 'Send to tutor', exact: true }).click()
  await expect.poll(() => calls).toBe(1)
  const node = await question.elementHandle()
  await page.screenshot({ path: info.outputPath('desktop-panel.png'), fullPage: true })
  await page.setViewportSize({ width: 390, height: 844 })
  await expect(panel).toBeVisible()
  expect(await node!.evaluate(element => element.isConnected)).toBe(true)
  await page.getByRole('button', { name: 'Close learning companion' }).focus()
  await page.keyboard.press('Shift+Tab')
  expect(await panel.evaluate(element => element.contains(document.activeElement))).toBe(true)
  await page.screenshot({ path: info.outputPath('narrow-sheet.png'), fullPage: true })
  await page.setViewportSize({ width: 320, height: 700 })
  expect(await panel.evaluate(element => element.scrollWidth <= element.clientWidth)).toBe(true)
  await page.keyboard.press('Tab')
  expect(await panel.evaluate(element => element.contains(document.activeElement))).toBe(true)
  await page.setViewportSize({ width: 1440, height: 900 })
  expect(await node!.evaluate(element => element.isConnected)).toBe(true)
  release()
  await expect(page.getByText('Reply after resize', { exact: true }).first()).toBeVisible()
  expect(calls).toBe(1)
  await page.setViewportSize({ width: 390, height: 844 })
  await expect.poll(() => panel.evaluate(element => element.matches(':modal'))).toBe(true)
  await page.keyboard.press('Escape')
  await expect(panel).not.toBeVisible()
  await expect(open).toBeFocused()
})
