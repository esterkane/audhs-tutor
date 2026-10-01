import { expect, test } from '@playwright/test'

test('authoring keeps draft, applied and saved state separate', async ({ page }) => {
  await page.goto('/playground/visualizer')
  await page.getByRole('button', { name: 'Create', exact: true }).click()
  await page.getByText('Add or remove blocks (optional)', { exact: true }).click()
  await page.getByRole('combobox', { name: 'New block type', exact: true }).selectOption('constant')
  await page.getByRole('button', { name: 'Add block', exact: true }).focus()
  await page.keyboard.press('Enter')
  await page.getByText('Block controls (4)', { exact: true }).click()
  await page.getByLabel('Value for constant_1', { exact: true }).fill('0.8')
  await page.getByLabel('Value for constant_1', { exact: true }).press('Enter')
  await page.getByText('Signal flow diagram', { exact: true }).click()
  await page.getByRole('combobox', { name: 'Source for visual size', exact: true }).selectOption('constant_1')
  await page.getByRole('button', { name: 'Undo draft', exact: true }).click()
  await expect(page.getByRole('combobox', { name: 'Source for visual size', exact: true })).toHaveValue(
    'size',
  )
  await page.getByRole('button', { name: 'Redo draft', exact: true }).click()
  await page.getByRole('combobox', { name: 'Block to remove', exact: true }).selectOption('constant_1')
  await page.getByRole('button', { name: 'Remove block', exact: true }).click()
  await expect(page.getByText(/Cannot remove constant_1: used by visual size/)).toBeVisible()
  await page.getByRole('button', { name: 'Apply preset', exact: true }).click()
  await page.getByRole('button', { name: 'Save applied preset', exact: true }).click()
  await page.reload()
  await page.getByRole('button', { name: 'Create', exact: true }).click()
  await page.getByText('Signal flow diagram', { exact: true }).click()
  await expect(page.getByRole('combobox', { name: 'Source for visual size', exact: true })).toHaveValue(
    'constant_1',
  )
  await page.getByText('Import or reset draft (optional)', { exact: true }).click()
  const upload = page.getByLabel('Choose preset JSON file', { exact: true })
  await upload.setInputFiles({
    name: 'bad.json',
    mimeType: 'application/json',
    buffer: Buffer.from('{"schemaVersion":99}'),
  })
  await expect(page.getByRole('alert')).toContainText('schemaVersion 1')
  await expect(page.getByRole('combobox', { name: 'Source for visual size', exact: true })).toHaveValue(
    'constant_1',
  )
  const candidate = {
    schemaVersion: 1,
    name: 'Imported experiment',
    nodes: [{ id: 'constructor', type: 'constant', value: 1 }],
    visual: { kind: 'bars', color: '#123456', scale: 'constructor', energy: 'constructor' },
  }
  await upload.setInputFiles({
    name: 'good.json',
    mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify(candidate)),
  })
  await expect(page.getByText(/Ready to import: Imported experiment/)).toBeVisible()
  await expect(page.getByRole('combobox', { name: 'Source for visual size', exact: true })).toHaveValue(
    'constant_1',
  )
  await page.getByRole('button', { name: 'Replace draft with imported preset', exact: true }).click()
  await expect(page.getByRole('combobox', { name: 'Source for visual size', exact: true })).toHaveValue(
    'constructor',
  )
  await page.getByRole('button', { name: 'Reset draft to applied settings', exact: true }).click()
  await expect(page.getByRole('combobox', { name: 'Source for visual size', exact: true })).toHaveValue(
    'constant_1',
  )
  await expect(page.getByRole('combobox', { name: 'Input', exact: true })).toHaveValue('demo')
})

test('canvas-first views preserve the player and draft with accessible still mode', async ({ page }) => {
  await page.goto('/playground/visualizer')
  const canvas = page.getByLabel('Audio-reactive visual preview', { exact: true })
  const start = page.getByRole('button', { name: 'Start demo', exact: true })
  expect((await canvas.boundingBox())!.y).toBeLessThan((await start.boundingBox())!.y)
  await start.click()
  await expect(page.getByText(/Demo running/)).toBeVisible()
  await page.getByRole('button', { name: 'Create', exact: true }).click()
  await page.getByRole('combobox', { name: 'Visual style' }).selectOption('bars')
  const before = await canvas.evaluate((c: HTMLCanvasElement) => c.toDataURL())
  await page.getByLabel('Visual color', { exact: true }).fill('#ff0000')
  expect(await canvas.evaluate((c: HTMLCanvasElement) => c.toDataURL())).not.toBe(before)
  await page.getByRole('button', { name: 'Undo draft', exact: true }).click()
  await expect(page.getByLabel('Visual color', { exact: true })).toHaveValue('#a78bfa')
  await page.getByRole('button', { name: 'Apply preset', exact: true }).click()
  await expect(page.getByText(/Demo running/)).toBeVisible()
  await page.getByRole('button', { name: 'Learn', exact: true }).click()
  await page.getByRole('button', { name: 'Watch', exact: true }).click()
  await expect(page.getByText(/Demo running/)).toBeVisible()
  await page.getByRole('button', { name: 'Pause demo', exact: true }).click()
  await page.getByRole('button', { name: 'Fullscreen', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Stop', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Exit fullscreen', exact: true }).click()
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  await page.screenshot({ path: '/tmp/audhs-watch-narrow.png', fullPage: true })
})

test('file playback survives view switches and resumes after hiding', async ({ page }) => {
  await page.goto('/playground/visualizer')
  await page.getByRole('button', { name: 'Open audio', exact: true }).click()
  const wav = Buffer.alloc(44 + 16000 * 2 * 10)
  wav.write('RIFF', 0)
  wav.writeUInt32LE(wav.length - 8, 4)
  wav.write('WAVEfmt ', 8)
  wav.writeUInt32LE(16, 16)
  wav.writeUInt16LE(1, 20)
  wav.writeUInt16LE(1, 22)
  wav.writeUInt32LE(16000, 24)
  wav.writeUInt32LE(32000, 28)
  wav.writeUInt16LE(2, 32)
  wav.writeUInt16LE(16, 34)
  wav.write('data', 36)
  wav.writeUInt32LE(wav.length - 44, 40)
  for (let i = 0; i < 160000; i++)
    wav.writeInt16LE(Math.round(4000 * Math.sin((2 * Math.PI * 440 * i) / 16000)), 44 + i * 2)
  await page
    .getByLabel('Audio file', { exact: true })
    .setInputFiles({ name: 'test.wav', mimeType: 'audio/wav', buffer: wav })
  await page.getByRole('button', { name: 'Play file silently' }).click()
  const timeline = page.getByRole('slider', { name: /^Playback timeline/ })
  await expect.poll(async () => Number(await timeline.inputValue())).toBeGreaterThan(0)
  await page.getByRole('button', { name: 'Create', exact: true }).click()
  await page.getByRole('button', { name: 'Apply preset', exact: true }).click()
  await page.getByRole('button', { name: 'Learn', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Pause file', exact: true })).toBeEnabled()
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { configurable: true, value: true })
    document.dispatchEvent(new Event('visibilitychange'))
  })
  await expect(page.getByRole('button', { name: 'Resume file', exact: true })).toBeVisible()
  const position = Number(await timeline.inputValue())
  await page.evaluate(() => {
    Object.defineProperty(document, 'hidden', { configurable: true, value: false })
    document.dispatchEvent(new Event('visibilitychange'))
  })
  await page.getByRole('button', { name: 'Resume file', exact: true }).click()
  await expect.poll(async () => Number(await timeline.inputValue())).toBeGreaterThan(position)
  await page.getByRole('button', { name: 'Pause file', exact: true }).click()
  const savedPosition = await timeline.inputValue()
  await page.getByRole('button', { name: 'Start test signal', exact: true }).click()
  await expect(page.getByLabel('Current measured values')).toContainText('RMS 0.14')
  await page.getByRole('button', { name: 'Return to previous audio', exact: true }).click()
  await expect(timeline).toHaveValue(savedPosition)
  await expect(page.getByRole('button', { name: 'Resume file', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Stop', exact: true }).click()
})

test('unavailable WebGL falls back without losing the draft or transport', async ({ page }) => {
  await page.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext
    HTMLCanvasElement.prototype.getContext = function (
      this: HTMLCanvasElement,
      kind: string,
      ...args: unknown[]
    ) {
      if (kind === 'webgl2') return null
      return Reflect.apply(original, this, [kind, ...args])
    } as typeof original
  })
  await page.goto('/playground/visualizer')
  await page.getByRole('button', { name: 'Start demo', exact: true }).click()
  await page.getByRole('combobox', { name: 'Visual engine', exact: true }).selectOption('milkdrop')
  await expect(page.getByText(/Rich visuals unavailable/)).toBeVisible()
  await expect(page.getByRole('combobox', { name: 'Visual engine', exact: true })).toHaveValue('graph')
  await expect(page.getByText(/Demo running/)).toBeVisible()
})

test('duplicate edits do not overwrite the original saved visual', async ({ page }) => {
  await page.goto('/playground/visualizer')
  await page.getByRole('button', { name: 'Create', exact: true }).click()
  await page.getByRole('button', { name: 'Save applied preset', exact: true }).click()
  await page.getByRole('button', { name: 'Watch', exact: true }).click()
  await page.getByText('Your saved visuals', { exact: true }).click()
  await page.getByRole('button', { name: 'Duplicate Bass rings', exact: true }).click()
  await page.getByRole('button', { name: 'Load Bass rings (copy)', exact: true }).click()
  await page.getByRole('button', { name: 'Create', exact: true }).click()
  await page.getByLabel('Visual color', { exact: true }).fill('#ff0000')
  await page.getByRole('button', { name: 'Apply preset', exact: true }).click()
  await page.getByRole('button', { name: 'Save applied preset', exact: true }).click()
  const items = await page.evaluate(
    () => JSON.parse(localStorage.getItem('audhs:visualizer:library:v2')!).items,
  )
  expect(items.find((x: { name: string }) => x.name === 'Bass rings').preset.visual.color).toBe('#a78bfa')
  expect(items.find((x: { name: string }) => x.name === 'Bass rings (copy)').preset.visual.color).toBe(
    '#ff0000',
  )
})

test('bundled MilkDrop presets render and switch in still mode', async ({ page }) => {
  await page.goto('/playground/visualizer')
  await page.getByRole('combobox', { name: 'Visual engine', exact: true }).selectOption('milkdrop')
  await expect(page.getByLabel('MilkDrop visual preview', { exact: true })).toBeVisible()
  await page.getByRole('combobox', { name: 'Rich visual', exact: true }).selectOption('1')
  await expect(page.getByRole('combobox', { name: 'Visual engine', exact: true })).toHaveValue('milkdrop')
  await page.screenshot({ path: '/tmp/audhs-milkdrop.png', fullPage: true })
})

test('lessons measure real tones and show identical-input comparisons', async ({ page }) => {
  await page.goto('/playground/visualizer')
  await page.getByRole('button', { name: 'Learn', exact: true }).click()
  await page.getByRole('button', { name: 'Start test signal', exact: true }).click()
  const values = page.getByLabel('Current measured values', { exact: true })
  await expect(values).toContainText('RMS 0.14')
  await page.getByRole('button', { name: 'Capture current picture', exact: true }).click()
  const snapshot = await page.getByRole('region', { name: 'Live audio measurements' }).innerText()
  expect(Math.abs(Number(snapshot.match(/Strongest bin: ([\d.]+)/)![1]) - 220)).toBeLessThan(24)
  await page.getByRole('slider', { name: /Test amplitude/ }).fill('0.4')
  await expect(values).toContainText('RMS 0.28')
  await page.getByRole('combobox', { name: 'Learning step' }).selectOption('1')
  await page.getByRole('slider', { name: /Test frequency/ }).fill('1000')
  await expect(values).toContainText(/strongest bin (984|990|1007)/)
  await page.getByRole('combobox', { name: 'Learning step' }).selectOption('2')
  await page.getByRole('combobox', { name: 'Test waveform' }).selectOption('square')
  await page.getByRole('combobox', { name: 'Learning step' }).selectOption('0')
  await expect(values).toContainText('RMS 0.28')
  await page.getByRole('combobox', { name: 'Learning step' }).selectOption('4')
  await page.getByRole('button', { name: 'Choose a frequency region', exact: true }).click()
  await page.getByRole('button', { name: 'Try change and compare', exact: true }).click()
  const before = await page
    .getByLabel('Before comparison: ring size 0.800')
    .evaluate((c: HTMLCanvasElement) => c.toDataURL())
  const after = await page
    .getByLabel('After comparison: ring size 0.200')
    .evaluate((c: HTMLCanvasElement) => c.toDataURL())
  expect(before).not.toBe(after)
  await page.getByRole('button', { name: 'Watch', exact: true }).click()
  await page.getByRole('combobox', { name: 'Visual engine', exact: true }).selectOption('milkdrop')
  await page.getByRole('button', { name: 'Capture current picture', exact: true }).click()
  await expect(page.getByLabel('MilkDrop visual preview')).toBeVisible()
  await expect
    .poll(async () =>
      page.getByLabel('MilkDrop visual preview').evaluate((c: HTMLCanvasElement) => {
        const gl = c.getContext('webgl2')!
        const pixels = new Uint8Array(c.width * c.height * 4)
        gl.readPixels(0, 0, c.width, c.height, gl.RGBA, gl.UNSIGNED_BYTE, pixels)
        return pixels.some((v, i) => i % 4 !== 3 && v > 10)
      }),
    )
    .toBe(true)
  await page.getByRole('button', { name: 'Fullscreen', exact: true }).click()
  await expect
    .poll(async () =>
      page.getByLabel('MilkDrop visual preview').evaluate((c: HTMLCanvasElement) => {
        const gl = c.getContext('webgl2')!
        const pixels = new Uint8Array(c.width * c.height * 4)
        gl.readPixels(0, 0, c.width, c.height, gl.RGBA, gl.UNSIGNED_BYTE, pixels)
        return pixels.some((v, i) => i % 4 !== 3 && v > 10)
      }),
    )
    .toBe(true)
  await page.getByRole('button', { name: 'Exit fullscreen', exact: true }).click()
  await page.screenshot({ path: '/tmp/audhs-tone-milkdrop.png', fullPage: true })
  await page.getByRole('button', { name: 'Learn', exact: true }).click()
  await page.getByRole('button', { name: 'Return to previous audio', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Resume demo', exact: true })).toBeVisible()
})

test('rich visuals animate only with motion enabled and survive input replacement', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'no-preference' })
  await page.route('**/api/preferences', (route) =>
    route.fulfill({ json: { values: { 'ui.reduced_motion': false, 'ui.sound': false } } }),
  )
  await page.goto('/playground/visualizer')
  await page.getByRole('button', { name: 'Learn', exact: true }).click()
  await page.getByRole('button', { name: 'Start test signal', exact: true }).click()
  await expect(page.getByLabel('Current measured values')).toContainText('RMS 0.14')
  await page.getByRole('button', { name: 'Watch', exact: true }).click()
  await page.getByRole('combobox', { name: 'Visual engine', exact: true }).selectOption('milkdrop')
  const rich = page.getByLabel('MilkDrop visual preview')
  const before = await rich.evaluate((c: HTMLCanvasElement) => c.toDataURL())
  await expect.poll(async () => rich.evaluate((c: HTMLCanvasElement) => c.toDataURL())).not.toBe(before)
  await page.getByRole('button', { name: 'Stop', exact: true }).click()
  await page.getByRole('button', { name: 'Learn', exact: true }).click()
  await page.getByRole('button', { name: 'Restart test signal', exact: true }).click()
  await expect(page.getByLabel('Current measured values')).toContainText('RMS 0.14')
  await page.getByRole('button', { name: 'Watch', exact: true }).click()
  await expect(rich).toBeVisible()
  await expect(page.getByRole('combobox', { name: 'Visual engine', exact: true })).toHaveValue('milkdrop')
  await page.getByRole('button', { name: 'Stop', exact: true }).click()
})

test('shortcuts open their destination and file chooser preserves playback until selection', async ({
  page,
}) => {
  await page.goto('/playground/visualizer')
  const canvas = page.getByLabel('Audio-reactive visual preview', { exact: true })
  const before = await canvas.evaluate((el: HTMLCanvasElement) => el.toDataURL())
  await page.getByRole('button', { name: 'Start demo', exact: true }).click()
  await expect.poll(() => canvas.evaluate((el: HTMLCanvasElement) => el.toDataURL())).not.toBe(before)
  const chooserEvent = page.waitForEvent('filechooser')
  await page.getByRole('button', { name: 'Open audio', exact: true }).click()
  const chooser = await chooserEvent
  await expect(page.getByRole('button', { name: 'Pause demo', exact: true })).toBeEnabled()
  await chooser.setFiles([])
  await expect(page.getByRole('combobox', { name: 'Input', exact: true })).toHaveValue('demo')
  await page.getByRole('button', { name: 'Learn how it works', exact: true }).click()
  await expect(page.locator('#visualizer-explanation')).toBeFocused()
  await expect(page.getByRole('region', { name: 'Audio lessons', exact: true })).toBeInViewport()
  await page.getByRole('button', { name: 'Create', exact: true }).click()
  await expect(page.locator('#visualizer-create')).toBeFocused()
  await page.getByRole('button', { name: 'Fullscreen', exact: true }).click()
  await page.getByRole('button', { name: 'Choose visual', exact: true }).click()
  await expect(page.locator('#visual-engine')).toBeFocused()
  await expect.poll(() => page.evaluate(() => document.fullscreenElement === null)).toBe(true)
  await page.getByRole('button', { name: 'Pause demo', exact: true }).click()
  await expect(page.getByRole('button', { name: /Resume demo/ })).toBeEnabled()
})
