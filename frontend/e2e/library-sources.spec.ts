import { expect, test } from '@playwright/test'

const hit = { chunk_id: 'passage-one', citation: 'Fixture source · section one', source_type: 'text', text: 'Compare representation before cleaning.', flagged: [], quarantined: false }
for (const width of [390, 1280]) {
  test(`Library source search and passage return ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    const searches: unknown[] = [], writes: string[] = []
    page.on('request', request => { if (request.method() !== 'GET' && request.url().includes('/api/') && !request.url().endsWith('/api/corpus/search')) writes.push(request.url()) })
    await page.route('**/api/corpus/search', route => {
      searches.push(route.request().postDataJSON())
      return route.fulfill({ json: { hits: [hit] } })
    })
    await page.route('**/api/curriculum/chunks/passage-one', route => route.fulfill({ json: {
      ...hit, citation: hit.citation, document_title: 'Fixture source', trust_tier: 2,
      text: 'Full passage with surrounding context.', prev_text: 'Earlier paragraph.', next_text: 'Following paragraph.', uri: 'local/source.txt', open_url: null,
    } }))
    await page.goto('/sources')
    await expect(page.getByRole('heading', { name: 'Library', exact: true })).toBeVisible()
    expect(searches).toEqual([])
    await expect(page.getByRole('navigation',{name:'Main navigation'}).getByRole('link',{name:'Library',exact:true})).toHaveAttribute('aria-current','page')
    await page.getByRole('searchbox', { name: 'Search phrase' }).fill('representation')
    await page.getByRole('searchbox', { name: 'Search phrase' }).press('Enter')
    const read = page.getByRole('button', { name: `Read passage: ${hit.citation}` })
    await expect(read).toBeVisible()
    expect(searches.length).toBeGreaterThan(0)
    for (const search of searches) expect(search).toEqual({ query: 'representation', k: 8, tutor_view: false })
    await read.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByText('Full passage with surrounding context.', { exact: true })).toBeVisible()
    await expect(page.locator('[aria-label="Selected source passage"]')).toBeFocused()
    await expect(page).toHaveURL(/passage=passage-one/)
    await page.reload()
    await expect(page.getByText('Full passage with surrounding context.', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: 'Close', exact: true }).focus()
    await page.keyboard.press('Enter')
    await expect(page).not.toHaveURL(/passage=/)
    await expect(read).toBeFocused()
    await expect(page.getByRole('searchbox', { name: 'Search phrase' })).toHaveValue('representation')
    await read.click()
    await page.getByRole('button', { name: 'Close', exact: true }).click()
    await expect(read).toBeFocused()
    await page.goBack()
    await expect(page.getByText('Full passage with surrounding context.', { exact: true })).toBeVisible()
    await page.goForward()
    await expect(page.getByText('Full passage with surrounding context.', { exact: true })).toHaveCount(0)
    await page.screenshot({ path: info.outputPath('sources.png'), fullPage: true })
    await page.addStyleTag({ content: 'html { font-size: 200% !important; }' })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
    expect(writes).toEqual([])
  })
}

test('Library retains query after a missing passage and can retry source search',async({page})=>{
 let failing=true
 await page.route('**/api/corpus/search',route=>route.fulfill(failing?{status:503,json:{}}:{json:{hits:[]}}))
 await page.route('**/api/curriculum/chunks/gone',route=>route.fulfill({status:404,json:{}}))
 await page.goto('/sources?q=missing&passage=gone')
 await expect(page.getByText(/This passage is no longer/)).toBeVisible()
 await page.getByRole('button',{name:'Close',exact:true}).click()
 await expect(page.getByRole('searchbox',{name:'Search phrase'})).toHaveValue('missing')
 await expect(page.getByRole('button',{name:'Retry source search'})).toBeVisible()
 failing=false;await page.getByRole('button',{name:'Retry source search'}).click()
 await expect(page.getByText('No indexed passages matched.',{exact:true})).toBeVisible()
 await page.getByRole('button',{name:'Clear search'}).click()
 await expect(page.getByRole('searchbox',{name:'Search phrase'})).toHaveValue('')
})

test('late source search does not replace the new query', async ({ page }) => {
  let release!: () => void, finish!: () => void, start!: () => void
  const pending = new Promise<void>(resolve => { release = resolve })
  const delivered = new Promise<void>(resolve => { finish = resolve })
  const started = new Promise<void>(resolve => { start = resolve })
  await page.route('**/api/corpus/search', async route => {
    const query = route.request().postDataJSON().query
    if (query === 'old') { start(); await pending }
    await route.fulfill({ json: { hits: [{ ...hit, citation: query }] } })
    if (query === 'old') finish()
  })
  await page.goto('/sources?q=old')
  await started
  await page.getByRole('searchbox', { name: 'Search phrase' }).fill('new')
  await page.getByRole('button', { name: 'Search', exact: true }).click()
  await expect(page.getByRole('button', { name: 'Read passage: new', exact: true })).toBeVisible()
  release()
  await delivered
  await expect(page.getByRole('button', { name: 'Read passage: old', exact: true })).toHaveCount(0)
})


test('long source names remain readable and retain full provenance in the passage',async({page})=>{
 const citation='uploadednotes'.repeat(35)+'.md'
 await page.setViewportSize({width:390,height:900})
 await page.route('**/api/corpus/search',route=>route.fulfill({json:{hits:[{...hit,chunk_id:'long-p',citation}]}}))
 await page.route('**/api/curriculum/chunks/long-p',route=>route.fulfill({json:{chunk_id:'long-p',citation,text:'Exact uploaded source context.',source_type:'text',document_title:citation,trust_tier:2,uri:'notes.md',open_url:null}}))
 await page.goto('/library?q=notes')
 const open=page.getByRole('button',{name:'Read passage: '+citation,exact:true})
 await expect(open).toBeVisible()
 expect((await open.innerText()).length).toBeLessThan(140)
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
 await open.click()
 await expect(page.getByText(citation,{exact:true})).toBeVisible()
 await expect(page.getByText('Exact uploaded source context.',{exact:true})).toBeVisible()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBeTruthy()
 await page.getByRole('button',{name:'Close',exact:true}).click()
 await expect(open).toBeFocused()
})
