import { expect, test } from '@playwright/test'

test('visualizer is explicit, editable, persistent and local', async ({ page }) => {
  const requests: string[] = []
  page.on('request', (r) => {
    if (r.method() !== 'GET') requests.push(r.url())
  })
  await page.goto('/areas')
  await page.getByRole('link', { name: 'Audio visualizer', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Audio visualizer lab' })).toBeVisible()
  await expect(page.getByLabel('Preset JSON', { exact: true })).not.toBeVisible()
  await page.screenshot({ path: '../data/visualizer-ux-default.png', fullPage: true })
  await expect(page.getByRole('button', { name: 'Start demo', exact: true })).toBeDisabled()
  await page.getByRole('button', { name: 'Next sample' }).click()
  await page.getByText('Walk through one sample', { exact: true }).click()
  await page.getByRole('button', { name: 'Start sample walkthrough', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Block 1 of 3: signal' })).toBeVisible()
  await page.getByRole('button', { name: 'Next block', exact: true }).click()
  await expect(page.getByText('Block output: 0.524', { exact: true })).toBeVisible()
  await page.getByText('Block controls (3)', { exact: true }).click()
  await page.getByRole('combobox', { name: 'Feature for signal', exact: true }).selectOption('treble')
  await expect(page.getByRole('button', { name: 'Start sample walkthrough', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Start sample walkthrough', exact: true }).click()
  await expect(page.getByText('Synthetic treble: 0.409', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'End walkthrough', exact: true }).click()
  await page.getByRole('button', { name: 'Explain signal', exact: true }).click()
  await expect(page.getByText(/signal reads treble/)).toBeVisible()
  await expect(page.getByText(/current visual values belong to the previous preset/)).toBeVisible()
  await page.getByLabel('Output start for size', { exact: true }).fill('0.8')
  await page.getByLabel('Output start for size', { exact: true }).press('Tab')
  await page.getByRole('button', { name: 'Apply preset', exact: true }).click()
  await expect(page.getByText(/Last displayed block value/)).toBeVisible()
  await page.getByText('Signal flow diagram', { exact: true }).click()
  const flow = page.getByRole('region', { name: 'Signal flow', exact: true })
  await expect(flow.getByText(/Applied connections/)).toBeVisible()
  await flow.getByRole('button', { name: 'Inspect size', exact: true }).first().click()
  await expect(page.getByRole('heading', { name: 'About size', exact: true })).toBeVisible()
  await expect(flow.getByText(/energy \(not used by rings\)/)).toBeVisible()
  await page.getByRole('button', { name: 'Open block canvas', exact: true }).click()
  const canvas = page.getByLabel('Interactive block canvas', { exact: true })
  const signal = canvas.locator('[data-id="signal"].react-flow__node')
  await expect(signal).toBeVisible()
  await signal.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('heading', { name: 'About signal', exact: true })).toBeVisible()
  const beforeDrag = await signal.boundingBox()
  if (!beforeDrag) throw new Error('Missing node bounds')
  await page.mouse.move(beforeDrag.x + 40, beforeDrag.y + 15)
  await page.mouse.down()
  await page.mouse.move(beforeDrag.x + 65, beforeDrag.y + 55, { steps: 8 })
  await page.mouse.up()
  const afterDrag = await signal.boundingBox()
  expect(afterDrag?.y).toBeGreaterThan(beforeDrag.y + 10)
  const from = await signal.locator('.react-flow__handle.source').boundingBox()
  const to = await canvas.locator('[data-id="size"] .react-flow__handle.target').boundingBox()
  if (!from || !to) throw new Error('Missing connector bounds')
  await page.mouse.move(from.x + from.width / 2, from.y + from.height / 2)
  await page.mouse.down()
  await page.mouse.move(to.x + to.width / 2, to.y + to.height / 2, { steps: 12 })
  await page.mouse.up()
  await expect(page.getByRole('combobox', { name: 'Input for size', exact: true })).toHaveValue('signal')
  await page.getByRole('combobox', { name: 'Input for size', exact: true }).selectOption('soft')
  await page.getByRole('combobox', { name: 'Input for size', exact: true }).selectOption('signal')
  await expect(flow.getByText(/Draft connections/)).toBeVisible()
  await page.getByRole('combobox', { name: 'Input for soft', exact: true }).selectOption('soft')
  await expect(page.getByRole('status').filter({ hasText: /cycl/i })).toBeVisible()
  await expect(page.getByRole('combobox', { name: 'Input for soft', exact: true })).toHaveValue('signal')
  await page.getByRole('button', { name: 'Apply preset', exact: true }).click()
  await expect(flow.getByText(/Applied connections/)).toBeVisible()
  await page.screenshot({ path: '../data/visualizer-block-editor-review.png', fullPage: true })
  await page.getByText('Advanced: edit preset JSON', { exact: true }).click()
  const editor = page.getByRole('textbox', { name: 'Preset JSON' })
  const original = await editor.inputValue()
  await editor.fill('{"broken":true}')
  await expect(page.getByText(/Fix the preset error or load an example before applying/)).toBeVisible()
  await expect(flow).toHaveCount(0)
  await page.getByRole('button', { name: 'Apply preset' }).click()
  await expect(page.getByRole('alert')).toContainText('last working preset')
  await expect(page.getByText(/Active preset: Bass rings/)).toBeVisible()
  const changed = JSON.parse(original)
  changed.nodes.push({ id: 'constructor', type: 'constant', value: 0.5 })
  changed.name = 'Browser test orbit'
  changed.visual.kind = 'orbit'
  await editor.fill(JSON.stringify(changed, null, 2))
  await page.getByRole('button', { name: 'Apply preset' }).click()
  await page.getByRole('button', { name: 'Save applied preset' }).click()
  await page.reload()
  await expect(page.getByText(/Active preset: Browser test orbit/)).toBeVisible()
  await page.getByText('Signal flow diagram', { exact: true }).click()
  await page.getByRole('button', { name: 'Open block canvas', exact: true }).click()
  await expect(page.locator('.react-flow__node[data-id="constructor"]')).toBeVisible()
  await page.getByRole('button', { name: 'Hide block canvas', exact: true }).click()
  await page.getByText('Guided Bass rings lesson', { exact: true }).click()
  await page.getByRole('button', { name: 'One hint' }).click()
  await expect(page.getByText(/Start with the feature node/)).toBeVisible()
  await page.getByRole('combobox', { name: 'Input', exact: true }).selectOption('file')
  // Generated two-tone WAV fixture; no purchased or personal audio. Playback stays muted.
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
    wav.writeInt16LE(
      Math.round(4000 * Math.sin((2 * Math.PI * (i < 80000 ? 440 : 880) * i) / 16000)),
      44 + i * 2,
    )
  await page
    .getByLabel('Audio file', { exact: true })
    .setInputFiles({ name: 'two-tones.wav', mimeType: 'audio/wav', buffer: wav })
  await expect(page.getByText(/Waveform ready/)).toBeVisible()
  await page.getByRole('button', { name: 'Show frequency view (optional)', exact: true }).click()
  await expect(page.getByText('Frequency view ready.', { exact: true })).toBeVisible()
  await expect(page.getByRole('region', { name: 'Low-frequency spectrogram' })).toBeVisible()
  await page.screenshot({ path: '../data/visualizer-frequency-review.png', fullPage: true })
  await page.getByRole('button', { name: 'Hide frequency view', exact: true }).click()
  await expect(page.getByText(/File selected. Press Play/)).toBeVisible()
  await page.getByRole('button', { name: 'Play file silently' }).click()
  await expect(
    page.getByText('Playing silently · picture stays still until you capture it', { exact: false }),
  ).toBeVisible()
  await page.getByRole('button', { name: 'Pause file', exact: true }).click()
  await expect(page.getByText(/Paused. Resume continues/)).toBeVisible()
  const timeline = page.getByRole('slider', { name: /^Playback timeline/ })
  await timeline.fill('3')
  await expect(page.getByText(/Playback position: 3.0 s/)).toBeVisible()
  await expect(timeline).toHaveValue('3')
  await page.getByText('Try a short comparison experiment', { exact: true }).click()
  await page.getByRole('button', { name: 'Follow changes gradually', exact: true }).click()
  await page.getByRole('button', { name: 'Try change and compare', exact: true }).click()
  await expect(page.getByRole('table')).toContainText('0.506')
  await expect(page.getByRole('table')).toContainText('0.145')
  await expect(timeline).toHaveValue('3')
  await expect(page.getByRole('button', { name: 'Resume file', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Restart experiment', exact: true }).click()
  await expect(page.getByRole('table')).toHaveCount(0)
  await page.getByRole('button', { name: 'Stop experiment', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Choose a frequency region', exact: true })).toBeVisible()
  await page.getByText('Repeat a short section (optional)', { exact: true }).click()
  await page.getByRole('spinbutton', { name: 'Section start (seconds)', exact: true }).fill('1')
  await page.getByRole('spinbutton', { name: 'Section end (seconds)', exact: true }).fill('2')
  await page.getByRole('button', { name: 'Enable repeat', exact: true }).click()
  await expect(page.getByText(/Repeat on: 1.0–2.0/)).toBeVisible()
  await expect(timeline).toHaveValue('1')
  await page.getByRole('button', { name: 'Resume file', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Pause file', exact: true })).toBeEnabled()
  let lastPosition = 0
  await expect
    .poll(
      async () => {
        const current = Number(await timeline.inputValue())
        const wrapped = current < lastPosition
        lastPosition = current
        return wrapped
      },
      { timeout: 8000, intervals: [150] },
    )
    .toBe(true)
  await page.getByRole('button', { name: 'Capture current picture' }).click()
  await page.getByRole('button', { name: 'Stop', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Capture current picture' })).toBeDisabled()
  await expect(timeline).toBeDisabled()
  await expect(page.getByRole('button', { name: 'Turn repeat off' })).toBeDisabled()
  expect(requests).toEqual([])
  await page.screenshot({ path: '../data/visualizer-audio-ux-review.png', fullPage: true })
})

test('beginner workspace preserves drafts on desktop and narrow screens', async ({ page }) => {
  await page.goto('/playground/visualizer')
  const picture = page.getByRole('combobox', { name: 'Visual style', exact: true })
  const preview = page.getByLabel('Audio-reactive visual preview', { exact: true })
  await expect(picture).toBeVisible()
  const controlBounds = await picture.boundingBox()
  const previewBounds = await preview.boundingBox()
  expect(controlBounds!.x).toBeGreaterThan(previewBounds!.x + previewBounds!.width)
  await picture.selectOption('bars')
  await expect(picture).toHaveValue('bars')
  await page.getByRole('button', { name: 'Apply preset', exact: true }).focus()
  await page.keyboard.press('Enter')
  await page.keyboard.press('Tab')
  await expect(page.getByRole('button', { name: 'Save applied preset', exact: true })).toBeFocused()
  await page.keyboard.press('Enter')
  await page.setViewportSize({ width: 390, height: 844 })
  await page.getByText('Advanced: edit preset JSON', { exact: true }).click()
  const before = await page.getByLabel('Preset JSON', { exact: true }).inputValue()
  await page.getByText('Walk through one sample', { exact: true }).click()
  await expect(page.getByLabel('Preset JSON', { exact: true })).not.toBeVisible()
  await page.getByText('Advanced: edit preset JSON', { exact: true }).click()
  await expect(page.getByLabel('Preset JSON', { exact: true })).toHaveValue(before)
  await expect(picture).toHaveValue('bars')
  await page.getByText('Advanced: edit preset JSON', { exact: true }).click()
  await page.screenshot({ path: '../data/visualizer-v1-narrow.png', fullPage: true })
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.screenshot({ path: '../data/visualizer-v1-desktop.png', fullPage: true })
})

test('authoring keeps draft, applied and saved state separate', async ({ page }) => {
  await page.goto('/playground/visualizer')
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
