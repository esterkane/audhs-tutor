import { expect, test } from '@playwright/test'
import { API } from './helpers'
import axe from 'axe-core'

for (const entry of ['/curriculum', '/preferences']) test(`explicit key save clears the field and keeps authoring mode and budget unchanged from ${entry}`,  async ({ page, request }) => {
  const before = await (await request.get(`${API}/api/authoring/setup`)).json()
  let saves = 0
  await page.route('**/api/authoring/key', async route => {
    expect(route.request().postDataJSON()).toEqual({ key: 'synthetic-browser-secret' })
    saves++
    await route.fulfill({ json: { ...before, key_configured: true } })
  })
  await page.setViewportSize({ width: 390, height: 900 })
  await page.goto(entry)
  await page.getByText('Authoring setup: OpenAI or local', { exact: true }).click()
  const input = page.getByLabel('OpenAI API key', { exact: true })
  const save = page.getByRole('button', { name: 'Save API key', exact: true })
  await expect(save).toBeDisabled()
  await input.fill('synthetic-browser-secret')
  await expect(page.getByText(/Key entered but not saved/)).toBeVisible()
  await save.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText('API key saved on this machine. No model request was made.')).toBeVisible()
  await expect(input).toHaveValue('')
  await expect(save).toBeDisabled()
  expect(saves).toBe(1)
  const after = await (await request.get(`${API}/api/authoring/setup`)).json()
  expect(after).toEqual(before) // intercepted secret never reached the sandbox or a provider
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
})


test('settings exposes one authoring form, truthful unavailable status and read-only retry', async ({page,request},testInfo) => {
  const before=await (await request.get(`${API}/api/authoring/setup`)).json()
  let recovered=false
  let writes=0
  page.on('request',r=>{if(r.url().includes('/api/') && ['PUT','POST','DELETE','PATCH'].includes(r.method())) writes++})
  await page.route('**/api/authoring/setup',route=>{
    return !recovered ? route.fulfill({status:503,json:{error:{message:'Synthetic unavailable'}}}) : route.fulfill({json:before})
  })
  await page.setViewportSize({width:390,height:900})
  await page.goto('/preferences')
  await page.getByText('Authoring setup: OpenAI or local',{exact:true}).click()
  await expect(page.getByText(/Current mode, key status and spending are unknown/)).toBeVisible()
  await expect(page.getByRole('button',{name:'Use OpenAI for authoring',exact:true})).toBeDisabled()
  recovered=true
  await page.getByRole('button',{name:'Retry authoring settings',exact:true}).click()
  await expect(page.getByText(/Authoring daily cap:/)).toBeVisible()
  await expect(page.getByText(/not two allowances to add together/)).toBeVisible()
  await expect(page.getByRole('slider',{name:'Maximum daily hosted authoring spend (US cents)'})).toHaveCount(0)
  await expect(page.getByRole('switch',{name:'Use OpenAI for knowledge authoring and factual reviews'})).toHaveCount(0)
  const violations=await page.evaluate(async(source)=>{eval(source);return (await (window as unknown as {axe: typeof axe}).axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa']}})).violations},axe.source)
  expect(violations).toEqual([])
  await page.getByRole('region',{name:'Knowledge authoring and factual reviews'}).screenshot({path:testInfo.outputPath('authoring-settings.png')})
  expect(writes).toBe(0)
  expect(await (await request.get(`${API}/api/authoring/setup`)).json()).toEqual(before)
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true)
})
