import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { chromium, expect, test } from '@playwright/test'
import { API, expectOk } from './helpers'

for (const { width, theme } of [{ width: 640, theme: 'light' }, { width: 1280, theme: 'dark' }]) test(`Task review at real 200% zoom ${theme}`, async ({ request, baseURL }, info) => {
  const extension = info.outputPath('zoom-extension')
  await mkdir(extension, { recursive: true })
  await writeFile(join(extension, 'manifest.json'), JSON.stringify({ manifest_version: 3, name: 'Isolated task review zoom', version: '1.0', permissions: ['tabs'], background: { service_worker: 'worker.js' } }))
  await writeFile(join(extension, 'worker.js'), 'chrome.runtime.onInstalled.addListener(() => {});')
  const context = await chromium.launchPersistentContext('', { channel: 'chromium', headless: true, baseURL, viewport: { width, height: 1800 }, reducedMotion: 'reduce', args: [`--disable-extensions-except=${extension}`, `--load-extension=${extension}`] })
  try {
    await expectOk(await request.put(`${API}/api/preferences`, { data: { key: 'ui.theme', value: theme } }))
    const page = await context.newPage()
    const writes: string[] = []
    page.on('request', req => { if (req.url().includes('/api/questions/') && req.method() !== 'GET') writes.push(req.url()) })
    await page.route('**/api/questions/example/task-review', route => route.fulfill({ json: { assessment_id: 'example', content_version: 'v1', current_review: null, approval_matches_content: false, reviewable: true, unavailable_reason: null, content: { objective: { title: 'Explain representation after cleaning' }, item: { prompt: 'Which groups could be excluded by removing incomplete rows?' }, criteria: [{ criterion: 'Explain a selection-bias mechanism with a concrete example' }] } } }))
    await page.goto('/task-review?assessment=example&returnTo=%2Fprogress')
    const worker = context.serviceWorkers()[0] ?? await context.waitForEvent('serviceworker')
    const actual = await worker.evaluate(async url => {
      const tabs = (globalThis as unknown as { chrome: { tabs: { query(options: object): Promise<Array<{ id?: number; url?: string }>>; setZoom(id: number, factor: number): Promise<void>; getZoom(id: number): Promise<number> } } }).chrome.tabs
      const tab = (await tabs.query({})).find(item => item.url === url)
      if (tab?.id === undefined) throw new Error('Test tab unavailable')
      await tabs.setZoom(tab.id, 2)
      return tabs.getZoom(tab.id)
    }, page.url())
    expect(actual).toBe(2)
    await expect.poll(() => page.evaluate(() => innerWidth)).toBe(width / 2)
    await expect.poll(() => page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe(theme === 'dark' ? 'rgb(29, 30, 36)' : 'rgb(247, 248, 252)')
    await page.getByRole('button', { name: 'Show task and rubric' }).focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('heading', { name: 'Content to review' })).toBeFocused()
    await expect(page.getByRole('button', { name: 'Approve this task review' })).toBeDisabled()
    await page.getByRole('combobox', { name: 'What does this task assess?' }).focus()
    await page.keyboard.press('Tab')
    await expect(page.getByRole('checkbox')).toBeFocused()
    await page.keyboard.press('Space')
    await page.keyboard.press('Tab')
    await expect(page.getByRole('button', { name: 'Approve this task review' })).toBeFocused()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    const cdp = await context.newCDPSession(page)
    const capture = await cdp.send('Page.captureScreenshot', { format: 'png' })
    await writeFile(info.outputPath('task-review-zoom.png'), Buffer.from(capture.data, 'base64'))
    await cdp.detach()
    await page.getByRole('button', { name: 'Close without changing review' }).focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('button', { name: 'Show task and rubric' })).toBeFocused()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('checkbox')).not.toBeChecked()
    expect(writes).toEqual([])
  } finally {
    await context.close()
    await expectOk(await request.put(`${API}/api/preferences`, { data: { key: 'ui.theme', value: 'light' } }))
  }
})
