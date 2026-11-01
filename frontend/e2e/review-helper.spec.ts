import { expect, test } from '@playwright/test'
import { finishReview } from './helpers'

test('review journey helper waits for ten cards across loading gaps', async ({ page }) => {
  // Reproduce CI's ten-card queue without changing the shared sandbox or skipping cards.
  await page.setContent('<main id="review"></main>')
  await page.evaluate(() => {
    let reviewed = 0
    const main = document.querySelector('main')!
    function showCard() {
      main.innerHTML = '<button>Show answer</button>'
      main.querySelector('button')!.onclick = () => {
        main.innerHTML = '<p>Answer</p><button>Good</button>'
        main.querySelector('button')!.onclick = () => {
          reviewed++
          main.innerHTML = '<p role="status">Loading next card…</p>'
          setTimeout(() => {
            if (reviewed === 10) main.innerHTML = '<h1>Review done</h1><p>10 ratings saved</p>'
            else showCard()
          }, 450)
        }
      }
    }
    showCard()
  })
  await finishReview(page)
  await expect(page.getByText('10 ratings saved', { exact: true })).toBeVisible()
})
