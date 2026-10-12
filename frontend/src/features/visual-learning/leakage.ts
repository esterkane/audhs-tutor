export type FitScope = 'train' | 'all'
export const objective = 'Explain why preprocessing must learn its parameters from training data only.'
export const source = 'https://scikit-learn.org/stable/common_pitfalls.html#data-leakage'
export function centering(scope: FitScope, heldOut: number) {
  if (!['train', 'all'].includes(scope) || !Number.isFinite(heldOut) || heldOut < 6 || heldOut > 20) throw new Error('Invalid experiment input')
  const train = [2, 4]
  const test = [heldOut, heldOut + 2]
  const fit = scope === 'train' ? train : [...train, ...test]
  const mean = fit.reduce((sum, value) => sum + value, 0) / fit.length
  return { train, test, mean, transformed: test.map(value => value - mean) }
}
export function feedback(answer: string) {
  if (answer === 'train') return 'Correct for this scenario: learn the imputation median from training patients, then apply that same value to held-out patients. Test data must not influence fitting.'
  if (answer === 'all') return 'Using all patients lets the held-out set influence the learned median. Even without using outcome labels, that leaks test information into preprocessing.'
  if (answer === 'separate') return 'A separate test median learns a new transformation from test data. Apply the training median instead, so evaluation uses the already-fitted procedure.'
  throw new Error('Choose a listed answer')
}
