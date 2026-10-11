import { expect, test } from '@playwright/test'

test('prepares a notebook from the app without a terminal or automatic cell execution', async ({ page }) => {
  await page.route('**/local-learning/program.json', (route) =>
    route.fulfill({
      json: {
        title: 'Local practice',
        courses: [{ id: 'fixture', title: 'Example', project: 'Study', status: 'Fixture', sections: [] }],
      },
    }),
  )
  await page.route('**/api/notebooks/status', (route) =>
    route.fulfill({ json: { service_id: '11111111-1111-4111-8111-111111111111', status: 'idle', message: 'Ready to prepare', url: null, course_id: '' } }),
  )
  let requests = 0
  await page.route('**/api/notebooks/start', (route) => {
    requests++
    expect(route.request().postDataJSON()).toMatchObject({ course_id: 'fixture', install: false })
    return route.fulfill({
      json: {
        request_id: route.request().postDataJSON().request_id, service_id: route.request().postDataJSON().service_id, status: 'ready',
        message: 'Prepared',
        url: 'http://127.0.0.1:8890/lab/tree/fixture/task.ipynb?token=fixture',
        course_id: 'fixture',
      },
    })
  })
  await page.goto('/programs')
  await page.getByText('Full course notebook and files', { exact: true }).click()
  await page.getByRole('button', { name: 'Open full course notebook tools', exact: true }).click()
  await page.setViewportSize({ width: 390, height: 844 })
  const prepare = page.getByRole('button', { name: 'Prepare and start notebook lab' })
  await prepare.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByRole('link', { name: 'Open prepared notebook in Jupyter' })).toHaveAttribute(
    'href',
    /\/fixture\/task.ipynb/,
  )
  expect(requests).toBe(1)
})

for (const width of [390, 1280]) {
  test(`stalled notebook status has keyboard recovery ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 })
    await page.route('**/local-learning/program.json', route => route.fulfill({ json: {
      title: 'Local practice', courses: [{ id: 'fixture', title: 'Example', project: 'Study', status: 'Fixture', sections: [] }],
    } }))
    let reads = 0
    let recovered = false
    let starts = 0
    await page.route('**/api/notebooks/status', route => {
      reads++
      if (!recovered) return // Reproduce a transport that never answers, including remounts.
      return route.fulfill({ json: { service_id: '11111111-1111-4111-8111-111111111111', status: 'idle', message: 'Ready after retry', url: null, course_id: '' } })
    })
    await page.route('**/api/notebooks/start', route => { starts++; return route.abort() })
    await page.goto('/programs')
    await page.getByText('Full course notebook and files', { exact: true }).click()
    await page.getByRole('button', { name: 'Open full course notebook tools', exact: true }).click()
    await expect(page.getByText('Checking local notebook setup…')).toBeVisible()
    const retry = page.getByRole('button', { name: 'Retry status' })
    await expect(retry).toBeVisible({ timeout: 20000 })
    const beforeRetry = reads
    recovered = true
    await retry.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByText('Ready after retry')).toBeVisible()
    expect(starts).toBe(0)
    expect(reads).toBe(beforeRetry + 1)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
    await page.getByRole('region', { name: 'Complete local notebook' }).screenshot({ path: `/tmp/notebook-status-${width}.png` })
  })
}


for (const width of [390, 1280]) {
  test(`lost setup reply recovers after reload without another installation ${width}`, async ({ page }) => {
    await page.setViewportSize({ width, height: 844 })
    await page.route('**/local-learning/program.json', route => route.fulfill({ json: {
      title: 'Local practice', courses: [{ id: 'fixture', title: 'Example', project: 'Study', status: 'Fixture', sections: [] }],
    } }))
    const service = '11111111-1111-4111-8111-111111111111'
    await page.route('**/api/notebooks/status', route => route.fulfill({ json: {
      service_id: service, status: 'idle', message: 'Ready to prepare', url: null, course_id: '',
    } }))
    let submissions = 0
    let command: Record<string, unknown> = {}
    await page.route('**/api/notebooks/start', route => {
      submissions++; command = route.request().postDataJSON()
      return route.abort('failed')
    })
    await page.route('**/api/notebooks/requests/**', route => {
      expect(route.request().method()).toBe('GET')
      expect(route.request().url()).toContain(command.request_id as string)
      return route.fulfill({ json: { ...command, status: 'ready', message: 'Recovered setup', url: 'http://127.0.0.1:8890/lab/tree/fixture/task.ipynb?token=fixture' } })
    })
    async function openTools() {
      await page.getByText('Full course notebook and files', { exact: true }).click()
      await page.getByRole('button', { name: 'Open full course notebook tools', exact: true }).click()
    }
    await page.goto('/programs'); await openTools()
    await page.getByRole('button', { name: 'Prepare and start notebook lab' }).click()
    await expect(page.getByText(/Setup acknowledgement is unavailable/)).toBeVisible()
    await page.reload() // The URL restores the notebook view directly.
    const check = page.getByRole('button', { name: 'Check setup status', exact: true })
    await check.focus(); await page.keyboard.press('Enter')
    await expect(page.getByRole('link', { name: 'Open prepared notebook in Jupyter' })).toBeVisible()
    expect(submissions).toBe(1)
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true)
    await page.getByRole('region', { name: 'Complete local notebook' }).screenshot({ path: `/tmp/notebook-command-${width}.png` })
    expect(await page.evaluate(() => Object.values(sessionStorage).some(v => String(v).includes('token=fixture')))).toBe(false)
  })
}
