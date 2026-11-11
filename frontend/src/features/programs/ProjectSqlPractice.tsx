import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import { useDraftRecovery } from '../curriculum/useDraftRecovery'

const statements = ['BEGIN READ ONLY;', 'SET LOCAL ROLE authenticated;', 'SELECT current_user;', 'ROLLBACK;']
const initial = { order: [2, 3, 0, 1], stage: 0, ending: '', query: '', compared: false }
type Practice = typeof initial

export function ProjectSqlPractice({ projectId }: { projectId: string }) {
  const saved = useDraftRecovery('sql-role-practice-v1:' + projectId, 1, JSON.stringify(initial))
  const [message, setMessage] = useState('')
  let work: Practice
  try {
    work = JSON.parse(saved.text)
    if (
      !Array.isArray(work.order) ||
      [...work.order].sort().join(',') !== '0,1,2,3' ||
      ![0, 1, 2].includes(work.stage) ||
      typeof work.ending !== 'string' ||
      typeof work.query !== 'string' ||
      typeof work.compared !== 'boolean'
    )
      throw new Error()
  } catch {
    return (
      <p role="alert">
        This tab’s SQL practice could not be restored.{' '}
        <Button variant="secondary" onClick={() => saved.reset(JSON.stringify(initial), 1)}>
          Restart SQL practice
        </Button>
      </p>
    )
  }
  function update(changes: Partial<Practice>, feedback = '') {
    saved.edit(JSON.stringify({ ...work, ...changes }))
    setMessage(feedback)
  }
  function move(index: number, delta: number) {
    const order = [...work.order]
    const dest = index + delta
    order[index] = work.order[dest]
    order[dest] = work.order[index]
    update({ order }, `Statement moved to position ${dest + 1}.`)
  }
  return (
    <Disclosure label="Practice a role check (optional)">
      <section aria-label="SQL role practice" className="grid gap-3">
        <p>
          In a disposable PostgreSQL lab where your login can assume the authenticated role, start a read-only
          transaction, assume that role locally, inspect the effective role, then explicitly roll back. This
          exercise runs no SQL. Your writing stays in this tab.
        </p>
        {work.stage === 0 && (
          <>
            <h3>Arrange the four statements</h3>
            <ol className="list-decimal pl-5">
              {work.order.map((id, i) => (
                <li key={id}>
                  <code>{statements[id]}</code>{' '}
                  {([-1, 1] as const).map((delta) => (
                    <Button
                      key={delta}
                      variant="secondary"
                      disabled={i + delta < 0 || i + delta >= work.order.length}
                      aria-label={`Move ${statements[id]} ${delta < 0 ? 'up' : 'down'}`}
                      onClick={() => move(i, delta)}
                    >
                      {delta < 0 ? 'Up' : 'Down'}
                    </Button>
                  ))}
                </li>
              ))}
            </ol>
            <Button
              onClick={() =>
                work.order.every((id, i) => id === i)
                  ? update({ stage: 1 }, 'Order checked. Try the missing statement.')
                  : setMessage(
                      'Start the transaction before changing role. Inspect the role after changing it and before ending the transaction.',
                    )
              }
            >
              Check order
            </Button>
          </>
        )}
        {work.stage === 1 && (
          <>
            <h3>Complete the transaction</h3>
            <pre>{statements.slice(0, 3).join('\n')}</pre>
            <label>
              Final statement
              <input
                className="block"
                value={work.ending}
                maxLength={120}
                onChange={(e) => update({ ending: e.target.value })}
              />
            </label>
            <Button
              onClick={() =>
                /^\s*(?:rollback|abort)(?:\s+(?:work|transaction))?(?:\s+and\s+no\s+chain)?\s*;?\s*$/i.test(
                  work.ending,
                )
                  ? update({ stage: 2 }, 'Rollback recognized. Try the whole task.')
                  : setMessage(
                      'This drill asks you to roll back. Use a single ROLLBACK or ABORT statement, without comments.',
                    )
              }
            >
              Check final statement
            </Button>
          </>
        )}
        {work.stage === 2 && (
          <>
            <h3>Write the complete role check</h3>
            <label>
              Your SQL
              <textarea
                className="block w-full"
                rows={5}
                maxLength={4000}
                value={work.query}
                onChange={(e) => update({ query: e.target.value, compared: false })}
              />
            </label>
            <Button disabled={!work.query.trim()} onClick={() => update({ compared: true })}>
              Compare with an example
            </Button>
            {work.compared && (
              <div>
                <pre>{statements.join('\n')}</pre>
                <p>
                  Compare the transaction mode, role scope, value inspected and transaction ending. Equivalent
                  SQL can differ. Checking the effective role alone does not test table access or row
                  policies.
                </p>
              </div>
            )}
          </>
        )}
        {work.stage > 0 && (
          <Button variant="secondary" onClick={() => update({ stage: work.stage - 1 })}>
            Revisit the previous step
          </Button>
        )}
        {message && <p role="status">{message}</p>}
        {saved.error && <p role="alert">{saved.error}</p>}
      </section>
    </Disclosure>
  )
}
