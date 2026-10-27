import { mkdir, writeFile } from 'node:fs/promises'
import { join } from 'node:path'
import { chromium, expect, test, type BrowserContext, type Page } from '@playwright/test'
import { API, currentSession, endOpenSession, expectOk } from './helpers'

type ZoomTabs = {
  query(options: Record<string, never>): Promise<Array<{ id?: number; url?: string }>>
  setZoom(id: number, factor: number): Promise<void>
  getZoom(id: number): Promise<number>
}

/** Real Chromium tab zoom, not CSS font-size or device-metrics emulation. */
async function setZoom(context: BrowserContext, page: Page, factor: number) {
  const worker = context.serviceWorkers()[0] ?? await context.waitForEvent('serviceworker')
  const actual = await worker.evaluate(async ({ url, factor }) => {
    const tabs = (globalThis as unknown as { chrome: { tabs: ZoomTabs } }).chrome.tabs
    const tab = (await tabs.query({})).find(item => item.url === url)
    if (tab?.id === undefined) throw new Error('Isolated test tab unavailable')
    await tabs.setZoom(tab.id, factor)
    return tabs.getZoom(tab.id)
  }, { url: page.url(), factor })
  expect(actual).toBe(factor)
}

for (const { width, theme } of [{ width: 640, theme: 'light' }, { width: 1280, theme: 'dark' }]) test(`real 200% browser zoom preserves learning at ${width / 2} CSS pixels in ${theme}`, async ({ request, baseURL }, info) => {
  const extension = info.outputPath('zoom-extension')
  await mkdir(extension, { recursive: true })
  await writeFile(join(extension, 'manifest.json'), JSON.stringify({
    manifest_version: 3, name: 'Isolated browser zoom check', version: '1.0',
    permissions: ['tabs'], background: { service_worker: 'worker.js' },
  }))
  await writeFile(join(extension, 'worker.js'), 'chrome.runtime.onInstalled.addListener(() => {});')
  // Empty userDataDir creates a disposable profile; never connect to the owner's browser.
  const context = await chromium.launchPersistentContext('', {
    channel: 'chromium', headless: true, baseURL,
    viewport: { width, height: 1800 }, reducedMotion: 'reduce',
    args: [`--disable-extensions-except=${extension}`, `--load-extension=${extension}`],
  })
  try {
    await endOpenSession(request)
    await expectOk(await request.put(`${API}/api/preferences`, { data: { key: 'ui.font_scale', value: 'normal' } }))
    await expectOk(await request.put(`${API}/api/preferences`, { data: { key: 'ui.theme', value: theme } }))
    for (const key of ['goal.area', 'goal.course']) await expectOk(await request.put(`${API}/api/preferences`, { data: { key, value: '' } }))
    const response = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
    await expectOk(response)
    const session = await response.json()
    const index = session.plan.findIndex((block: { type: string }) => block.type === 'new_material')
    await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }))
    const before = await currentSession(request)
    const page = await context.newPage()
    const writes: string[] = []
    const preferenceWrites: unknown[] = []
    page.on('request', r => { if (r.url().endsWith('/api/preferences') && r.method() === 'PUT') { preferenceWrites.push(r.postDataJSON()); return } if (r.url().includes('/api/') && r.method() !== 'GET' && !r.url().endsWith('/prepare') && !r.url().endsWith('/api/corpus/search')) writes.push(r.url()) })
    await page.goto('/')
    const rootSize = await page.evaluate(() => getComputedStyle(document.documentElement).fontSize)
    await setZoom(context, page, 2)
    await expect.poll(() => page.evaluate(() => innerWidth)).toBe(width / 2)
    expect(await page.evaluate(() => devicePixelRatio)).toBe(2)
    expect(await page.evaluate(() => getComputedStyle(document.documentElement).fontSize)).toBe(rootSize)
    const resume = page.getByRole('button', { name: 'Continue', exact: true })
    await resume.focus()
    await page.keyboard.press('Enter')
    const draft = page.getByLabel('Ask about this lesson (optional)')
    await draft.fill('Keep my question through real browser zoom')
    await expect.poll(() => page.evaluate(() => getComputedStyle(document.body).backgroundColor)).toBe(theme === 'dark' ? 'rgb(29, 30, 36)' : 'rgb(247, 248, 252)')
    const pause = page.getByRole('button', { name: 'Pause and return Home', exact: true })
    await pause.focus()
    await page.keyboard.press('Tab')
    await expect(page.getByRole('button', { name: 'Focus on lesson', exact: true })).toBeFocused()
    await page.keyboard.press('Tab')
    const options = page.locator('summary').filter({ hasText: /^Session options$/ })
    await expect(options).toBeFocused()
    await page.keyboard.press('Enter')
    await page.keyboard.press('Tab')
    await expect(page.getByRole('button', { name: 'End session', exact: true })).toBeFocused()
    await page.keyboard.press('Tab')
    await expect(page.getByRole('button', { name: 'Change topic', exact: true })).toBeFocused()
    await page.keyboard.press('Shift+Tab')
    await page.keyboard.press('Shift+Tab')
    await expect(options).toBeFocused()
    await page.keyboard.press('Enter')
    await page.keyboard.press('Tab')
    const more=page.locator('summary').filter({hasText:/^More session tools$/})
    await more.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('heading',{name:'Learning context',exact:true})).toBeVisible()
    await more.focus()
    await page.keyboard.press('Enter')
    await expect(more).toBeFocused()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.evaluate(() => window.scrollTo(0, 0))
    await expect.poll(() => page.evaluate(() => scrollY)).toBe(0)
    // Capture the compositor surface directly: Playwright full-page capture clips
    // to CSS dimensions when extension-driven browser zoom changes devicePixelRatio.
    const cdp = await context.newCDPSession(page)
    const capture = await cdp.send('Page.captureScreenshot', { format: 'png' })
    await writeFile(info.outputPath('lesson-200-percent.png'), Buffer.from(capture.data, 'base64'))
    await cdp.detach()
    await page.getByRole('link', { name: 'Settings', exact: true }).focus()
    await page.keyboard.press('Enter')
    const largeText = page.getByRole('button', { name: 'Large', exact: true })
    await expect(largeText).toBeVisible()
    await largeText.focus()
    await page.keyboard.press('Enter')
    await expect(largeText).toHaveAttribute('aria-pressed', 'true')
    await expect.poll(() => page.evaluate(() => parseFloat(getComputedStyle(document.documentElement).fontSize))).toBeGreaterThan(parseFloat(rootSize))
    expect(preferenceWrites).toEqual([{ key: 'ui.font_scale', value: 'large' }])
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.getByRole('button', { name: 'Back', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(draft).toHaveValue('Keep my question through real browser zoom')
    await page.getByRole('button', { name: 'Pause and return Home', exact: true }).focus()
    await page.keyboard.press('Enter')
    await resume.focus()
    await page.keyboard.press('Enter')
    await expect(draft).toHaveValue('Keep my question through real browser zoom')
    await page.reload()
    await expect(draft).toHaveValue('Keep my question through real browser zoom')
    // Browse another topic without losing the active session or draft at real zoom.
    const skillList = await (await request.get(`${API}/api/skills`)).json()
    expect(before?.state?.skill_id).toBeTruthy()
    const selectedSkill = skillList.skills.find((skill: { id: string }) => skill.id !== before?.state?.skill_id)
    expect(selectedSkill).toBeTruthy()
    await page.route('**/api/areas', route => route.fulfill({ json: {
      areas: [{ id: 'zoom-area', title: 'Example area', description: 'Browse concepts', terms: ['example'], active_lessons: 1 }],
      total_documents: 0, unassigned_documents: 0,
    } }))
    await page.route('**/api/areas/zoom-area/concepts', route => route.fulfill({ json: {
      area_id: 'zoom-area', concepts: [selectedSkill],
    } }))
    await page.getByRole('link', { name: 'Progress', exact: true }).focus()
    await page.keyboard.press('Enter')
    await page.getByRole('link', { name: 'Explore by area', exact: true }).focus()
    await page.keyboard.press('Enter')
    await page.getByRole('link', { name: 'Example area', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('heading', { name: selectedSkill.title, exact: true })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await page.getByRole('link', { name: 'Choose this lesson', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('heading', { level: 1, name: `Learn: ${selectedSkill.title}`, exact: true })).toBeVisible()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    const selectionCapture = await context.newCDPSession(page)
    const selectionImage = await selectionCapture.send('Page.captureScreenshot', { format: 'png' })
    await writeFile(info.outputPath('selection-200-percent.png'), Buffer.from(selectionImage.data, 'base64'))
    await selectionCapture.detach()
    await page.getByRole('button', { name: 'Keep current session', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(draft).toHaveValue('Keep my question through real browser zoom')
    // Search is read-only and must preserve the same learning checkpoint at real zoom.
    await page.route('**/api/areas', route => route.fulfill({ json: { areas: [], total_documents: 0, unassigned_documents: 0 } }))
    await page.route('**/local-learning/program.json', route => route.fulfill({ status: 404, json: {} }))
    await page.route('**/api/answers?*', route => route.fulfill({ json: { items: [], next_cursor: null } }))
    await page.route('**/api/corpus/search', route => route.fulfill({ json: { hits: [{
      chunk_id: 'zoom-source', citation: 'A source with a long descriptive title for comparing evidence',
      text: 'Inspect the evidence before drawing a conclusion.', source_type: 'text', flagged: [], quarantined: false,
    }] } }))
    const searchEntry = page.locator('header').getByRole('button', { name: 'Search or go to', exact: true })
    await searchEntry.focus()
    await page.keyboard.press('Enter')
    await page.getByRole('button', { name: 'Open material search', exact: true }).focus()
    await page.keyboard.press('Enter')
    const search = page.getByRole('searchbox', { name: 'Search phrase' })
    await search.fill('evidence')
    await search.press('Enter')
    const groups = page.getByRole('navigation', { name: 'Search result groups' })
    await expect(groups).toBeVisible()
    for (const link of await groups.getByRole('link').all()) {
      expect((await link.boundingBox())?.height).toBeGreaterThanOrEqual(44)
    }
    await groups.getByRole('link', { name: 'Source passages', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('heading', { name: 'Source passages', exact: true })).toBeFocused()
    await page.keyboard.press('Tab')
    await expect(page.getByRole('button', { name: 'Read passage: A source with a long descriptive title for comparing evidence' })).toBeFocused()
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    await groups.scrollIntoViewIfNeeded()
    const searchCapture = await context.newCDPSession(page)
    const searchImage = await searchCapture.send('Page.captureScreenshot', { format: 'png' })
    await writeFile(info.outputPath('search-200-percent.png'), Buffer.from(searchImage.data, 'base64'))
    await searchCapture.detach()
    await page.reload()
    await expect(search).toHaveValue('evidence')
    await page.getByRole('link', { name: 'Home', exact: true }).focus()
    await page.keyboard.press('Enter')
    await page.getByRole('button', {name:'Continue',exact:true}).focus()
    await page.keyboard.press('Enter')
    await expect(draft).toHaveValue('Keep my question through real browser zoom')
    await setZoom(context, page, 1)
    await expect.poll(() => page.evaluate(() => innerWidth)).toBe(width)
    await expect(draft).toHaveValue('Keep my question through real browser zoom')
    expect(await currentSession(request)).toEqual(before)
    expect(writes).toEqual([])
    expect(preferenceWrites).toEqual([{ key: 'ui.font_scale', value: 'large' }])
  } finally {
    await expectOk(await request.put(`${API}/api/preferences`, { data: { key: 'ui.font_scale', value: 'normal' } }))
    await context.close()
    await endOpenSession(request)
    await expectOk(await request.put(`${API}/api/preferences`, { data: { key: 'ui.theme', value: 'light' } }))
  }
})
