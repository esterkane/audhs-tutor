import { test, expect } from '@playwright/test'
import { API, expectOk } from '../e2e/helpers'
test('preserve personal writing while researching and resolve an oversized section', async ({
  page,
  request,
}) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/curriculum')
  const title = 'Synthetic personal lesson on privileges'
  const notes = 'An application role requires a table SELECT grant to read rows.'
  await page.getByLabel('Material title', { exact: true }).fill(title)
  await page.getByLabel('Your notes and selected source content').fill(notes)
  const writes: string[] = []
  page.on('request', (req) => {
    if (req.method() === 'POST') writes.push(req.url())
  })
  await page.getByRole('button', { name: 'Write a lesson from my notes' }).press('Enter')
  await expect(page.getByRole('heading', { name: 'Write your knowledge section' })).toBeFocused()
  await expect(page.getByRole('button', { name: 'Prepare research questions' })).toBeHidden()
  await page.getByText('Read your source notes', { exact: true }).click()
  await expect(
    page.getByRole('region', { name: 'Write a lesson from your notes' }).getByText(notes, { exact: true }),
  ).toBeVisible()
  const explanation = 'A SELECT privilege allows a table read operation.'
  await page.getByLabel('Learning objective', { exact: true }).fill('Identify the required table privilege.')
  await page.getByLabel('Explanation', { exact: true }).fill(explanation)
  await page.reload()
  await expect(page.getByLabel('Explanation', { exact: true })).toHaveValue(explanation)
  await page
    .getByLabel('Worked example', { exact: true })
    .fill('A missing table grant denies the read operation.')
  await page.getByLabel('Application question', { exact: true }).fill('Which grant permits a table read?')
  await page.getByLabel(/Success criteria/).fill('Identifies SELECT.')
  const researchText = 'A row security policy can limit rows even after the table privilege check.'
  await page.getByRole('button', { name: '2. Research', exact: true }).click()
  await page.getByRole('button', { name: '3. Write', exact: true }).click()
  await expect(page.getByRole('textbox', { name: 'Explanation', exact: true })).toHaveValue(explanation)
  await page.getByRole('button', { name: '2. Research', exact: true }).click()
  await page.getByRole('button', { name: '3. Write', exact: true }).click()
  await page.getByRole('textbox', { name: 'Explanation', exact: true }).fill(explanation.padEnd(3998, 'x'))
  await page.getByRole('button', { name: '2. Research', exact: true }).click()
  await page.getByLabel('Topic to investigate').fill('Privilege and visibility')
  await page.getByRole('button', { name: 'Use notes as passage' }).click()
  await page.getByRole('button', { name: 'Prepare research questions' }).click()
  await page.getByLabel('My findings', { exact: true }).fill(researchText)
  await page.getByRole('button', { name: '3. Write', exact: true }).click()
  await page.getByLabel('My knowledge section', { exact: true }).fill(researchText)
  const append = page.getByRole('button', { name: 'Add section to explanation' })
  await expect(append).toBeDisabled()
  await expect(append).toHaveAccessibleDescription(/exceed 4,000/)
  await page.getByText('Edit existing explanation', { exact: true }).click()
  await expect(page.getByRole('textbox', { name: 'Existing lesson explanation' })).toHaveValue(
    explanation.padEnd(3998, 'x'),
  )
  await page.getByRole('textbox', { name: 'Existing lesson explanation' }).fill(explanation)
  await expect(page.getByLabel('My knowledge section', { exact: true })).toHaveValue(researchText)
  await append.click()
  await expect(page.getByRole('button', { name: 'Add section to explanation' })).toBeDisabled()
  await page.reload()
  await expect(page.getByLabel('My knowledge section', { exact: true })).toHaveValue(researchText)
  await page.getByRole('button', { name: 'Next', exact: true }).press('Enter')
  await expect(page.getByRole('heading', { name: 'Review your material' })).toBeFocused()
  await expect(page.getByRole('article', { name: 'Knowledge material preview' })).toContainText(explanation)
  const saving = page.waitForResponse((r) => r.url().endsWith('/drafts') && r.request().method() === 'POST')
  await page.getByRole('button', { name: 'Save knowledge material', exact: true }).click()
  await expectOk(await saving)
  const accepting = page.waitForResponse(
    (r) => r.url().endsWith('/publish') && r.request().method() === 'POST',
  )
  await page.getByRole('button', { name: 'Activate lessons', exact: true }).click()
  await expectOk(await accepting)
  const skills = (await (await request.get(API + '/api/skills')).json()).skills
  const skill = skills.find((s: { title: string }) => s.title === title)
  const reading = await (
    await request.get(API + '/api/knowledge-material/skills/' + skill.id + '/reading')
  ).json()
  expect(reading.notes).toEqual(notes)
  expect(reading.explanation).toEqual(explanation + '\n\n' + researchText)
  expect(reading.worked_example).toEqual('A missing table grant denies the read operation.')
  expect(writes.filter((url) => /uploads|research|tutor|generate/.test(url))).toEqual([])
})
