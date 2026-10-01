import { expect, test } from '@playwright/test'
import { API, currentSession, endOpenSession, expectOk, reachLearnBlock, skillIdBySlug } from './helpers'

/**
 * The CodeMirror exercise editor (ADR-0013) in a real browser: typing with Python auto-indent, Tab
 * indenting inside the editor, Escape-then-Tab leaving it (no keyboard trap), the draft surviving a
 * reload, and the plain-editor switch keeping the code. No code is run: Pyodide is not needed here.
 * `getByText` appears only for the disclosure line and status copy; `.cm-line` is CodeMirror's
 * public line element (the editor's textbox *is* the content element).
 */

test.beforeEach(async ({ request }) => endOpenSession(request))
test.afterEach(async ({ request }) => endOpenSession(request))

test('the code editor indents, releases focus after Escape and keeps the draft across a reload', async ({
  page,
  request,
}) => {
  await reachLearnBlock(page)
  // point the running learn block at the skill that has a code exercise
  const session = await currentSession(request)
  const skillId = await skillIdBySlug(request, 'attn-scaled')
  const moved = await request.post(`${API}/api/sessions/${session!.id}/checkpoint`, {
    data: { skill_id: skillId },
  })
  await expectOk(moved)
  await page.reload()
  await expect(page.getByRole('heading', { name: 'Learn: Scaled dot-product attention' })).toBeVisible()

  await page.getByText(/^Code exercise \(optional/).click()
  const editor = page.getByRole('textbox', { name: /Your code \(Python; Tab indents/ })
  await expect(editor).toBeVisible()
  await expect(editor).toContainText('def softmax(x):')
  const secondLine = editor.locator('.cm-line').nth(1)

  // replace the starter code; Enter after a colon auto-indents, Tab indents further
  await editor.click()
  await page.keyboard.press('ControlOrMeta+a')
  await page.keyboard.type('def f():')
  await page.keyboard.press('Enter')
  await page.keyboard.type('return 1')
  await expect(secondLine).toContainText('return 1')
  const indentOf = (line: string) => line.length - line.trimStart().length
  const before = indentOf(await secondLine.innerText())
  await page.keyboard.press('Tab')
  await expect.poll(async () => indentOf(await secondLine.innerText())).toBeGreaterThan(before)

  // Escape arms "next Tab leaves" without a time limit: a pause and an arrow key do not disarm it
  await page.keyboard.press('Escape')
  await page.waitForTimeout(2500)
  await page.keyboard.press('ArrowLeft')
  await page.keyboard.press('Tab')
  const switchButton = page.getByRole('button', { name: 'Switch to the plain editor' })
  await expect(switchButton).toBeFocused()
  // re-entering the editor (on the second line) restores Tab = indent
  await secondLine.click()
  const again = indentOf(await secondLine.innerText())
  await page.keyboard.press('Tab')
  await expect.poll(async () => indentOf(await secondLine.innerText())).toBeGreaterThan(again)

  // the draft is restored after a reload and announced
  await page.reload()
  await page.getByText(/^Code exercise \(optional/).click()
  await expect(page.getByRole('status').filter({ hasText: 'Your saved draft was restored' })).toBeVisible()
  await expect(page.getByRole('textbox', { name: /Tab indents/ })).toContainText('return 1')

  // the plain editor holds the same code; Reset returns the starter code
  await page.getByRole('button', { name: 'Switch to the plain editor' }).click()
  const plain = page.getByRole('textbox', { name: /Tab inserts two spaces/ })
  await expect(plain).toHaveValue(/return 1/)
  await page.getByRole('button', { name: 'Reset to starter code' }).click()
  await expect(plain).toHaveValue(/def softmax\(x\):/)
})
