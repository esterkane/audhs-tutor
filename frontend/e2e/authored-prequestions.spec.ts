import { expect, test } from '@playwright/test'
import axe from 'axe-core'
import { API, endOpenSession, expectOk } from './helpers'

for (const width of [390, 1280]) {
  test(
    'authored passage questions preserve reading and resume ' + width,
    async ({ page, request }, testInfo) => {
      page.setDefaultTimeout(15000)
      await endOpenSession(request)
      const title = 'Synthetic passage prediction ' + width
      const explanationQuestion = 'What changes when SELECT is allowed but no rows satisfy the policy?'
      const exampleQuestion = 'Which permission should be checked before investigating row visibility?'
      try {
        const created = await request.post(API + '/api/knowledge-material/drafts', {
          headers: { 'Idempotency-Key': crypto.randomUUID() },
          data: {
            title,
            domain: 'programming',
            notes: 'Synthetic source notes: privileges and visibility are separate.',
            objective: 'Distinguish SELECT privileges from row visibility.',
            explanation:
              'A table SELECT privilege permits the operation. A row policy can then restrict visible rows.',
            worked_example:
              'An ordinary application role with SELECT but no applicable row policy sees no rows.',
            question: 'Does a row policy grant the SELECT table privilege?',
            criteria: ['No. Table privileges are a separate prerequisite.'],
            workflow_step: 'review',
          },
        })
        await expectOk(created)
        const draft = await created.json()
        await page.setViewportSize({ width, height: 900 })
        await page.goto('/curriculum?draft=' + draft.id)
        if (
          !(await page
            .locator('summary')
            .filter({ hasText: 'Shape a lesson (optional)' })
            .evaluate((el) => (el.parentElement as HTMLDetailsElement).open))
        ) {
          await page.locator('summary').filter({ hasText: 'Shape a lesson (optional)' }).click()
        }
        await page
          .getByRole('textbox', { name: 'Before-reading question for explanation (optional)', exact: true })
          .fill(explanationQuestion)
        await page
          .getByRole('textbox', {
            name: 'Before-reading question for worked example (optional)',
            exact: true,
          })
          .fill(exampleQuestion)
        const saved = page.waitForResponse(
          (r) => r.url().endsWith('/drafts/' + draft.id) && r.request().method() === 'PUT',
        )
        await page.getByRole('button', { name: 'Save knowledge material', exact: true }).click()
        await expectOk(await saved)
        await page.reload()
        if (
          !(await page
            .locator('summary')
            .filter({ hasText: 'Shape a lesson (optional)' })
            .evaluate((el) => (el.parentElement as HTMLDetailsElement).open))
        ) {
          await page.locator('summary').filter({ hasText: 'Shape a lesson (optional)' }).click()
        }
        await expect(
          page.getByRole('textbox', {
            name: 'Before-reading question for explanation (optional)',
            exact: true,
          }),
        ).toHaveValue(explanationQuestion)
        const published = page.waitForResponse(
          (r) => r.url().endsWith('/drafts/' + draft.id + '/publish') && r.request().method() === 'POST',
        )
        await page.getByRole('button', { name: 'Activate lessons', exact: true }).click()
        const activation = await published
        await expectOk(activation)
        const activeDraft = await activation.json()
        const skills = (await (await request.get(API + '/api/skills')).json()).skills
        const skill = skills.find((s: { title: string }) => s.title === title)
        expect(skill).toBeTruthy()
        const readingUrl = API + '/api/knowledge-material/skills/' + skill.id + '/reading'
        const accepted = await (await request.get(readingUrl)).json()
        expect(accepted.prequestions).toHaveLength(2)
        expect(accepted.question).toBe('Does a row policy grant the SELECT table privilege?')
        const revisionResponse = await request.post(
          API + '/api/knowledge-material/drafts/' + draft.id + '/revise',
          {
            headers: { 'Idempotency-Key': crypto.randomUUID() },
            data: { expected_version: activeDraft.draft.version },
          },
        )
        await expectOk(revisionResponse)
        const revision = await revisionResponse.json()
        await expectOk(
          await request.put(API + '/api/knowledge-material/drafts/' + revision.id, {
            data: {
              ...Object.fromEntries(
                Object.entries(revision.payload.authoring).filter(([key]) =>
                  [
                    'title',
                    'domain',
                    'notes',
                    'objective',
                    'explanation',
                    'worked_example',
                    'question',
                    'criteria',
                    'workflow_step',
                    'explanation_prequestion',
                    'worked_example_prequestion',
                  ].includes(key),
                ),
              ),
              expected_version: revision.version,
              explanation_prequestion: 'An unpublished replacement question must not appear in reading.',
            },
          }),
        )
        expect(await (await request.get(readingUrl)).json()).toEqual(accepted)
        let generations = 0
        page.on('request', (r) => {
          if (/tutor\/(stream|study)/.test(r.url()) && r.method() === 'POST') generations++
        })
        await page.goto('/?lesson=' + encodeURIComponent(skill.id))
        const started = page.waitForResponse(
          (r) => r.url().endsWith('/api/sessions') && r.request().method() === 'POST',
        )
        await page.getByRole('button', { name: 'Start this lesson', exact: true }).click()
        const response = await started
        await expectOk(response)
        const session = await response.json()
        await expectOk(
          await request.post(API + '/api/plan/blocks/start', {
            data: {
              session_id: session.id,
              index: session.plan.findIndex((b: { type: string }) => b.type === 'new_material'),
            },
          }),
        )
        await page.goto('/session')
        await expect(page.getByText(explanationQuestion, { exact: false })).toBeVisible()
        await page.getByLabel('Your prediction (optional)').fill('I expect the role to see no rows.')
        await page.getByRole('button', { name: 'Save prediction and read', exact: true }).click()
        await page.getByRole('button', { name: 'Next section', exact: true }).click()
        await expect(page.getByText(exampleQuestion, { exact: false })).toBeVisible()
        await page.getByRole('button', { name: 'Read without predicting', exact: true }).click()
        await page.getByLabel('Your notes for this section (optional)').fill('Keep the two checks separate.')
        await page.reload()
        await expect(page.getByLabel('Your notes for this section (optional)')).toHaveValue(
          'Keep the two checks separate.',
        )
        await page.getByRole('button', { name: 'Previous section', exact: true }).click()
        await expect(page.getByText('I expect the role to see no rows.', { exact: true })).toBeVisible()
        await page.addScriptTag({ content: axe.source })
        expect(
          await page.evaluate(
            async () => (await (window as unknown as { axe: typeof axe }).axe.run('main')).violations,
          ),
        ).toEqual([])
        expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
        await page.screenshot({ path: testInfo.outputPath('authored-prequestion.png'), fullPage: true })
        expect(generations).toBe(0)
        expect(await (await request.get(readingUrl)).json()).toEqual(accepted)
      } finally {
        await endOpenSession(request)
      }
    },
  )
}
