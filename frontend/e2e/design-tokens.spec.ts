import { readFile, writeFile } from 'node:fs/promises'
import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk } from './helpers'

for (const theme of ['light', 'dark', 'system-light', 'system-dark']) {
  for (const width of [390, 1280]) {
    test(`lesson input and code tokens ${theme} ${width}`, async ({ page, request }, info) => {
      await endOpenSession(request)
      try {
        await page.setViewportSize({ width, height: 900 })
        await page.emulateMedia({ colorScheme: theme.endsWith('dark') ? 'dark' : 'light' })
        await page.route('**/api/preferences', route => route.fulfill({ json: { values: {
          'ui.theme': theme.startsWith('system') ? 'system' : theme,
          'ui.font_scale': width === 390 ? 'large' : 'normal',
          'ui.reduced_motion': true,
        } } }))
        const started = await request.post(`${API}/api/sessions`, { data: { mode: 'steady', energy: 3 } })
        await expectOk(started)
        const session = await started.json()
        const index = session.plan.findIndex((b: { type: string }) => b.type === 'new_material')
        await expectOk(await request.post(`${API}/api/plan/blocks/start`, { data: { session_id: session.id, index } }))
        const text = 'Use `remaining / starting` to compare rates.\n\n```python\nrate = 80 / 100\n```'
        await page.route('**/api/tutor/stream', route => route.fulfill({ contentType: 'text/event-stream', body:
          `event: token\ndata: ${JSON.stringify({ text })}\n\nevent: done\ndata: ${JSON.stringify({ turn_id: 'token-fixture', outcome: 'ok', text, sources: [], dropped: [], flagged: [] })}\n\n`,
        }))
        await page.goto('/')
        await page.getByRole('button', { name: /^Resume previous session/ }).click()
        const input = page.getByLabel('Ask about this lesson (optional)')
        await input.fill('x'.repeat(4001))
        const send = page.getByRole('button', { name: 'Send lesson question' })
        await expect(send).toBeDisabled()
        const disabledStyle = await send.evaluate(el => {
          const style = getComputedStyle(el)
          return { opacity: style.opacity, background: style.backgroundColor }
        })
        expect(disabledStyle.opacity).toBe('1')
        expect(disabledStyle.background).toBe(theme.endsWith('dark') ? 'rgb(22, 23, 28)' : 'rgb(238, 241, 247)')
        await input.fill('Show a code example.')
        await page.getByRole('button', { name: 'Send lesson question' }).click()
        await expect(page.locator('.prose p code').first()).toBeVisible()
        await input.fill('Keep this next question.')
        await send.focus()
        await expect(send).toBeFocused()
        const buttonBoundary = await send.evaluate(el => {
          const s = getComputedStyle(el)
          const root = getComputedStyle(document.documentElement)
          return { border: s.borderTopColor, control: root.getPropertyValue('--color-control').trim() }
        })
        expect(buttonBoundary.border).toBe(theme.endsWith('dark') ? 'rgb(127, 135, 151)' : 'rgb(125, 139, 163)')
        await input.focus()
        await page.keyboard.type(' More detail.')
        await expect(input).toHaveValue('Keep this next question. More detail.')
        const metrics = await input.evaluate(el => {
          const style = getComputedStyle(el)
          const inline = getComputedStyle(document.querySelector('.prose p code')!)
          const block = getComputedStyle(document.querySelector('.prose pre code')!)
          const lum = (color: string) => {
            const values = color.match(/[\d.]+/g)!.slice(0, 3).map(Number).map(v => v / 255)
              .map(v => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4)
            return values[0] * 0.2126 + values[1] * 0.7152 + values[2] * 0.0722
          }
          const contrast = (a: string, b: string) => (Math.max(lum(a), lum(b)) + 0.05) / (Math.min(lum(a), lum(b)) + 0.05)
          return { border: style.borderTopColor, surface: style.backgroundColor,
            boundaryContrast: contrast(style.borderTopColor, style.backgroundColor),
            focusContrast: contrast(style.outlineColor, style.backgroundColor), outlineWidth: style.outlineWidth,
            inlineBackground: inline.backgroundColor, inlineContrast: contrast(inline.color, inline.backgroundColor),
            blockCodeBackground: block.backgroundColor, overflow: document.documentElement.scrollWidth > innerWidth }
        })
        const canonical = JSON.parse(await readFile(new URL('../../docs/design/source/tokens.json', import.meta.url), 'utf8'))
        const applied = await page.evaluate(() => Object.fromEntries(['bg', 'fg', 'muted', 'card', 'line', 'control', 'code', 'accent', 'accent-fg', 'ok', 'warn', 'focus-ring', 'sunken', 'faint', 'accent-hover'].map(name => [name, getComputedStyle(document.documentElement).getPropertyValue(`--color-${name}`).trim()])))
        for (const [name, value] of Object.entries(applied)) {
          expect(value).toBe(canonical.color.tokens.find((token: { name: string }) => token.name === name).value[theme.endsWith('dark') ? 'dark' : 'light'])
        }
        await writeFile(info.outputPath('tokens.json'), JSON.stringify(metrics, null, 2))
        await page.screenshot({ path: info.outputPath('lesson.png'), fullPage: true })
        expect(metrics.boundaryContrast).toBeGreaterThanOrEqual(3)
        expect(metrics.inlineContrast).toBeGreaterThanOrEqual(4.5)
        expect(metrics.blockCodeBackground).toBe('rgba(0, 0, 0, 0)')
        expect(metrics.focusContrast).toBeGreaterThanOrEqual(3)
        expect(metrics.outlineWidth).toBe('2px')
        expect(metrics.overflow).toBe(false)
        await page.getByRole('button', { name: 'Pause and return Home', exact: true }).click()
        await page.getByRole('button', { name: /^Resume previous session/ }).click()
        await expect(input).toHaveValue('Keep this next question. More detail.')
      } finally { await endOpenSession(request) }
    })
  }
}
