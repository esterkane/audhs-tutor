import { expect, test } from '@playwright/test'

for (const width of [390, 1280]) {
  test(`Home separates continue from an explicit session switch ${width}`, async ({ page }, info) => {
    await page.setViewportSize({ width, height: 900 })
    const skill = { id: 'next', title: 'Next lesson', slug: 'next', domain: 'ai_ml', description: '', success_criteria: [], prerequisites: [], mastery: 0, unlocked: true, state: {} }
    const state = { skill_id: 'old-skill', block_status: 'running', phase: 'teach', plan_complete: false }
    const original = { id: 'old', active_skill: { ...skill, id: 'old-skill', title: 'Original lesson' }, next_skill: skill, state, plan: [], due_reviews: 0 }
    const writes: string[] = []
    await page.route('**/api/sessions/current', route => route.fulfill({ json: original }))
    await page.route('**/api/sessions/old', route => route.fulfill({ json: original }))
    await page.route('**/api/skills', route => route.fulfill({ json: { skills: [skill], next_skill_id: skill.id } }))
    await page.route('**/api/preferences', route => route.fulfill({ json: { values: {}, specs: [] } }))
    await page.route('**/api/sessions/selection/next', route => route.fulfill({ json: skill }))
    await page.route('**/api/sessions/old/end', route => {
      writes.push('end old')
      return route.fulfill({ json: { ...original, ended_at: 'now' } })
    })
    await page.route('**/api/sessions', route => {
      writes.push('start next')
      expect(route.request().postDataJSON().skill_id).toBe('next')
      return route.fulfill({ status: 201, json: { ...original, id: 'new', active_skill: skill, state: { ...state, skill_id: 'next' } } })
    })
    await page.goto('/')
    const resume = page.getByRole('button', { name: 'Continue', exact: true })
    await expect(resume).toBeVisible()
    await expect(page.getByLabel('Saved session').getByText('Original lesson', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Choose whether to switch' })).not.toBeVisible()
    await page.screenshot({ path: info.outputPath('resume-card.png'), fullPage: true })
    const disclosure = page.getByText('Start a different session', { exact: true })
    await disclosure.focus()
    await page.keyboard.press('Enter')
    await page.getByRole('button', { name: 'Choose whether to switch' }).click()
    await expect(page).toHaveURL(/\?lesson=next$/)
    await expect(page.getByRole('button', { name: 'Keep current session' })).toBeVisible()
    expect(writes).toEqual([])
    await page.getByRole('button', { name: 'Keep current session' }).click()
    await expect(page).toHaveURL(/\/session$/)
    expect(writes).toEqual([])
    await page.goto('/')
    await disclosure.click()
    await page.getByRole('button', { name: 'Choose whether to switch' }).click()
    await page.getByRole('button', { name: 'End and start this lesson' }).click()
    await expect(page).toHaveURL(/\/session$/)
    expect(writes).toEqual(['end old', 'start next'])
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true)
  })
}
