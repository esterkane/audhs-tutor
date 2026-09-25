import { expect, test } from '@playwright/test'
import { API, endOpenSession, expectOk, skillIdBySlug } from './helpers'

test.beforeEach(async ({ request }) => {
  await endOpenSession(request)
  await request.put(`${API}/api/preferences`, { data: { key: 'goal.area', value: '' } })
  await request.put(`${API}/api/preferences`, { data: { key: 'goal.course', value: '' } })
})
test.afterEach(async ({ request }) => endOpenSession(request))

for (const running of [false, true]) {
  test(`map choice survives the real session checkpoint (existing=${running})`, async ({ page, request }) => {
    const chosen = await skillIdBySlug(request, 'softmax')
    const skill = await (await request.get(`${API}/api/skills`)).json()
    const title = skill.skills.find((s: { id: string }) => s.id === chosen).title
    let oldId: string | undefined
    if (running) {
      const old = await request.post(`${API}/api/sessions`, { data: {} })
      await expectOk(old)
      oldId = (await old.json()).id
    }
    await page.goto('/map')
    const row = page.getByRole('listitem').filter({ hasText: title })
    await row.getByRole('button', { name: 'Learn this', exact: true }).click()
    await expect(page.getByRole('heading', { name: `Learn: ${title}`, exact: true })).toBeVisible()
    if (oldId) {
      expect((await (await request.get(`${API}/api/sessions/current`)).json()).id).toBe(oldId)
      await page.getByRole('button', { name: 'Keep current session', exact: true }).click()
      expect((await (await request.get(`${API}/api/sessions/current`)).json()).id).toBe(oldId)
      await page.goto(`/?lesson=${chosen}`)
    }
    await page
      .getByRole('button', { name: running ? 'End and start this lesson' : 'Start this lesson', exact: true })
      .click()
    await expect(page).toHaveURL(/\/session$/)
    const active = await (await request.get(`${API}/api/sessions/current`)).json()
    expect(active.state.skill_id).toBe(chosen)
    expect(active.checkpoint.skill_id).toBe(chosen)
    expect(active.active_skill.id).toBe(chosen)
    if (oldId)
      expect((await (await request.get(`${API}/api/sessions/${oldId}`)).json()).ended_at).not.toBeNull()
    await page.reload()
    await expect(page.getByText(title, { exact: false }).first()).toBeVisible()
    expect((await (await request.get(`${API}/api/sessions/current`)).json()).state.skill_id).toBe(chosen)
  })
}
