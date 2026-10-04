import { writeFile } from 'node:fs/promises'
import { expect, test } from '@playwright/test'
import axe from 'axe-core'

// Evidence collection, not a conformance gate: inspect findings, not the pass count.
test.skip(process.env.AUDHS_UX_AUDIT !== '1', 'Opt-in Phase 2 audit.')
const routes = ['/', '/areas', '/programs', '/playground', '/playground/visualizer', '/answers', '/map', '/together', '/experiments', '/vocab', '/corpus', '/curriculum', '/models', '/preferences', '/session', '/review', '/recap']
for (const width of [390, 800, 1280, 1920]) {
  test(`screen inventory ${width}px`, async ({ page }, info) => {
    test.setTimeout(180_000)
    await page.setViewportSize({ width, height: 900 })
    // Keep private programme manifests out of shareable evidence.
    await page.route('**/local-learning/program.json', route => route.fulfill({ json: { title: 'Audit fixture', courses: [] } }))
    const findings = []
    for (const path of routes) {
      await page.goto(path)
      await expect(page.getByRole('main')).toBeVisible()
      // Repeatable observation point, not proof every background job is finished.
      await page.waitForTimeout(500)
      await page.addScriptTag({ content: axe.source })
      const result = await page.evaluate(async () => {
        const audit = await (window as unknown as { axe: typeof axe }).axe.run(document, {
          runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa', 'best-practice'] },
        })
        return {
          title: document.title, width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
          headings: Array.from(document.querySelectorAll('main h1,main h2,main h3')).map(n => ({level:n.tagName,text:n.textContent})),
          text: document.querySelector('main')?.textContent?.slice(0, 5000),
          violations: audit.violations.map(v => ({ id:v.id, impact:v.impact, description:v.description, nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary})) })),
          incomplete: audit.incomplete.map(v => v.id),
        }
      })
      findings.push({ path, ...result })
      if (['/', '/preferences', '/playground', '/models'].includes(path))
        await page.screenshot({ path:info.outputPath(`${path.replaceAll('/','') || 'home'}.png`),fullPage:true })
    }
    await writeFile(info.outputPath('inventory.json'), JSON.stringify(findings,null,2))
  })
}

for (const path of ['/preferences','/map','/vocab','/experiments','/models']) {
  test(`backend failure evidence ${path}`, async ({ page }, info) => {
    await page.route('**/api/**', route => route.fulfill({ status:503,json:{detail:'Audit fixture: backend unavailable'} }))
    await page.goto(path)
    // Include the default query retry window before classifying terminal presentation.
    await page.waitForTimeout(9000)
    const text = await page.getByRole('main').innerText()
    await writeFile(info.outputPath('failure.json'), JSON.stringify({path,text},null,2))
    await page.screenshot({path:info.outputPath('failure.png'),fullPage:true})
    await expect(page.getByRole('link',{name:'Home',exact:true})).toBeVisible()
  })
}
