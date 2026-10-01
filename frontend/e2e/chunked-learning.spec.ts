import { expect, test } from '@playwright/test'

const programme = {
  title: 'Synthetic learning programme',
  courses: [
    {
      id: 'fixture',
      title: 'Reason about data',
      project: 'Write an evidence-based report',
      status: 'Synthetic fixture',
      sections: [
        {
          id: 'clean',
          title: 'Inspect missing values',
          explanation: 'Count missing rows within each group before changing the dataset.',
          example:
            'Group A retains 90 of 100 rows. Group B retains 60 of 100. The same rule has different effects.',
          task: 'Compare retention rates.',
          question: 'Why can the same rule affect groups differently?',
          hint: 'Compare the denominators.',
          criteria: 'Explain the different retention rates.',
          source: 'Authored synthetic example',
          challenges: [
            {
              id: 'transfer',
              question: 'Would filling every blank with zero solve the problem?',
              hint: 'What would zero mean?',
              criteria: 'Discuss meaning and distortion.',
            },
          ],
        },
        {
          id: 'report',
          title: 'Report limitations',
          explanation: 'Distinguish observed results from wider claims.',
          task: 'Write one limitation.',
          question: 'What has not been measured?',
          hint: 'Consider a new population.',
          criteria: 'Name missing evidence.',
          source: 'Authored synthetic example',
        },
      ],
    },
  ],
}

for (const narrow of [false, true]) {
  test(`chunked lesson: ${narrow ? 'narrow large text' : 'desktop'} keyboard, recovery and pause`, async ({
    page,
  }, info) => {
    await page.route('**/local-learning/program.json', (route) => route.fulfill({ json: programme }))
    await page.goto('/programs')
    if (narrow) await page.setViewportSize({ width: 390, height: 844 })
    await page.evaluate((large) => {
      document.documentElement.dataset.theme = large ? 'light' : 'dark'
      document.documentElement.style.fontSize = large ? '200%' : '100%'
    }, narrow)
    await expect(page.getByRole('heading', { name: 'Worked example' })).toBeVisible()
    await expect(page.getByRole('textbox', { name: 'Your explanation', exact: true })).toHaveCount(0)
    const deeper = page.getByRole('button', { name: 'Think deeper', exact: true })
    await deeper.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByRole('heading', { name: 'Explain your reasoning' })).toBeFocused()
    await page
      .getByRole('textbox', { name: 'Your explanation', exact: true })
      .fill('The groups lose different proportions.')
    await page.getByRole('combobox', { name: 'Question to explore' }).selectOption('challenge:transfer')
    await expect(page.getByRole('textbox', { name: 'Your explanation', exact: true })).toHaveValue('')
    await page
      .getByRole('textbox', { name: 'Your explanation', exact: true })
      .fill('Zero may be an invented measurement.')
    await page.getByRole('button', { name: 'Pause study', exact: true }).click()
    await expect(page.getByRole('button', { name: 'Listen to explanation' })).toHaveCount(0)
    await page.getByRole('button', { name: 'Resume this step' }).click()
    await page.reload()
    await expect(page.getByRole('textbox', { name: 'Your explanation', exact: true })).toHaveValue(
      'Zero may be an invented measurement.',
    )
    await page.getByRole('combobox', { name: 'Question to explore' }).selectOption('original')
    await expect(page.getByRole('textbox', { name: 'Your explanation', exact: true })).toHaveValue(
      'The groups lose different proportions.',
    )
    await page.evaluate((large) => {
      document.documentElement.dataset.theme = large ? 'light' : 'dark'
      document.documentElement.style.fontSize = large ? '200%' : '100%'
    }, narrow)
    const overflow = await page.evaluate(() =>
      [...document.querySelectorAll('body *')]
        .filter((e) => e.getBoundingClientRect().right > innerWidth + 1)
        .map((e) => ({
          tag: e.tagName,
          class: e.className,
          width: e.getBoundingClientRect().width,
          text: e.textContent?.slice(0, 60),
        })),
    )
    expect(
      await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1),
      JSON.stringify(overflow),
    ).toBe(true)
    await page.screenshot({ path: info.outputPath('lesson-reading.png'), fullPage: true })
  })
}
