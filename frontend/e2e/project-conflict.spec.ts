import { expect, test } from '@playwright/test'
import { API_URL } from '../playwright.config'

test('compare conflicting project writing across tabs and choose either version', async ({page,context,request}) => {
  const rows = await (await request.get(API_URL + '/api/projects')).json()
  const id = rows.find((row: {slug:string}) => row.slug === 'postgresql-query-plan').id
  const other = await context.newPage()
  for (const tab of [page,other]) {
    await tab.goto('/projects?project='+id)
    await expect(tab.getByLabel('My project notes')).toBeVisible()
  }
  const notes = page.getByLabel('My project notes')
  const serverNotes = other.getByLabel('My project notes')
  const save = page.getByRole('button',{name:'Save project notes'})
  const saveOther = other.getByRole('button',{name:'Save project notes'})
  const compare = page.getByRole('region',{name:'Compare project versions'})
  for (const choice of ['saved','local']) {
    await notes.fill('Writing in this tab '+choice)
    await serverNotes.fill('Another tab saved '+choice)
    await saveOther.click()
    await expect(other.getByRole('status')).toContainText('Project writing saved')
    await save.click()
    await expect(compare.getByText('Saved version: Another tab saved '+choice)).toBeVisible()
    await expect(compare.getByText('This tab: Writing in this tab '+choice)).toBeVisible()
    await expect(save).toBeDisabled()
    if (choice === 'saved') {
      await compare.getByRole('button',{name:'Use saved version'}).press('Enter')
      await expect(notes).toHaveValue('Another tab saved saved')
    } else {
      await compare.getByRole('button',{name:'Keep my writing against the latest version'}).press('Enter')
      await save.click()
      await expect(page.getByRole('status')).toContainText('Project writing saved')
      await other.reload()
      await expect(serverNotes).toHaveValue('Writing in this tab local')
    }
    await expect(compare).toHaveCount(0)
  }
})
