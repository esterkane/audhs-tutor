import { act, renderHook } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { jsonResponse } from '../../test/utils'
import { assessmentRecoveryKey, useAssessmentSubmission } from './useAssessmentSubmission'

const body = {
  session_id: 'session',
  assessment_id: 'item',
  answer: 'original',
  latency_ms: 42,
  hint_count: 0,
}
const reply = {
  assessment_id: 'item',
  attempt_id: 'attempt',
  feedback: 'Original feedback',
  next_step: 'Next',
  answer_id: 'answer',
}
function setup(session = 'session') {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return renderHook(({ session }) => useAssessmentSubmission(session), {
    initialProps: { session },
    wrapper: ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    ),
  })
}
beforeEach(() => sessionStorage.clear())
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

it('persists before POST, blocks changed retries, reloads and checks without grading', async () => {
  const fetcher = vi.fn(async (_url: string, init?: RequestInit) => {
    if (init?.method === 'POST') {
      const pending = JSON.parse(sessionStorage.getItem(assessmentRecoveryKey('session'))!)
      expect(pending.body).toEqual(body)
      expect((init.headers as Record<string, string>)['Idempotency-Key']).toBe(pending.id)
      throw new Error('Lost response')
    }
    return jsonResponse({ status: 'completed', result: reply })
  })
  vi.stubGlobal('fetch', fetcher)
  const first = setup()
  await act(async () => {
    await expect(
      first.result.current.mutateAsync({ ...body, questionLabel: 'Original question' }),
    ).rejects.toThrow('Lost response')
  })
  await act(async () => {
    await expect(first.result.current.mutateAsync({ ...body, answer: 'edited' })).rejects.toThrow(
      'earlier submission',
    )
  })
  expect(fetcher).toHaveBeenCalledTimes(1)
  first.unmount()
  const resumed = setup()
  expect(resumed.result.current.recovery.pending?.question).toBe('Original question')
  await act(async () => {
    await resumed.result.current.recovery.check()
  })
  expect(resumed.result.current.recovery.lookup?.result?.feedback).toBe('Original feedback')
  expect(fetcher).toHaveBeenCalledTimes(2)
  expect(fetcher.mock.calls[1][1]?.method).toBeUndefined()
})

it('only explicitly resends a missing request with the original frozen body and identity', async () => {
  const fetcher = vi.fn(async (_url: string, init?: RequestInit) =>
    init?.method === 'POST' ? jsonResponse(reply) : jsonResponse({ status: 'not_found', result: null }),
  )
  vi.stubGlobal('fetch', fetcher)
  const id = crypto.randomUUID()
  sessionStorage.setItem(
    assessmentRecoveryKey('session'),
    JSON.stringify({ version: 1, id, endpoint: '/api/challenge/submit', body, question: 'Original' }),
  )
  const hook = setup()
  await act(async () => {
    await hook.result.current.recovery.resend()
  })
  expect(fetcher).not.toHaveBeenCalled()
  await act(async () => {
    await hook.result.current.recovery.check()
  })
  await act(async () => {
    await hook.result.current.recovery.resend()
  })
  expect(fetcher.mock.calls[1][0]).toBe('/api/challenge/submit')
  expect(fetcher.mock.calls[1][1]?.body).toBe(JSON.stringify(body))
  expect((fetcher.mock.calls[1][1]?.headers as Record<string, string>)['Idempotency-Key']).toBe(id)
  expect(hook.result.current.recovery.lookup?.status).toBe('completed')
})

it('does not send when storage fails', async () => {
  const fetcher = vi.fn()
  vi.stubGlobal('fetch', fetcher)
  const hook = setup()
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('quota')
  })
  await act(async () => {
    await expect(hook.result.current.mutateAsync(body)).rejects.toThrow('No answer was sent')
  })
  expect(fetcher).not.toHaveBeenCalled()
})

it('bounds an abort-resistant request and ignores its late result', async () => {
  vi.useFakeTimers()
  let release!: (response: Response) => void
  vi.stubGlobal(
    'fetch',
    vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          release = resolve
        }),
    ),
  )
  const hook = setup()
  let sent!: Promise<unknown>
  await act(async () => {
    sent = hook.result.current.mutateAsync(body).catch((error) => error)
  })
  await act(async () => {
    await vi.advanceTimersByTimeAsync(15001)
  })
  expect(await sent).toBeInstanceOf(Error)
  expect(sessionStorage.getItem(assessmentRecoveryKey('session'))).not.toBeNull()
  await act(async () => {
    release(jsonResponse(reply))
    await Promise.resolve()
  })
  expect(sessionStorage.getItem(assessmentRecoveryKey('session'))).not.toBeNull()
})

it('never clears a newer pending identity from another mounted surface', async () => {
  const first = {
    version: 1,
    id: crypto.randomUUID(),
    endpoint: '/api/assess/attempt',
    body,
    question: 'One',
  }
  sessionStorage.setItem(assessmentRecoveryKey('session'), JSON.stringify(first))
  const hook = setup()
  const newer = { ...first, id: crypto.randomUUID() }
  sessionStorage.setItem(assessmentRecoveryKey('session'), JSON.stringify(newer))
  act(() => hook.result.current.recovery.clear())
  expect(JSON.parse(sessionStorage.getItem(assessmentRecoveryKey('session'))!).id).toBe(newer.id)
  expect(hook.result.current.recovery.pending?.id).toBe(newer.id)
})

for (const failure of ['getItem', 'setItem', 'malformed'] as const) {
  it(`explicit memory fallback keeps a frozen identity after ${failure} failure`, async () => {
    const session = `memory-${failure}`
    const submission = { ...body, session_id: session }
    if (failure === 'malformed') sessionStorage.setItem(assessmentRecoveryKey(session), '{broken')
    else
      vi.spyOn(Storage.prototype, failure).mockImplementation(() => {
        throw new Error('blocked')
      })
    const fetcher = vi.fn(async (_url: string, init?: RequestInit) => {
      if (init?.method === 'POST') throw new Error('Lost response')
      return jsonResponse({ status: 'not_found', result: null })
    })
    vi.stubGlobal('fetch', fetcher)
    const hook = setup(session)
    await act(async () => {
      await expect(hook.result.current.mutateAsync(submission)).rejects.toThrow()
    })
    expect(fetcher).not.toHaveBeenCalled()
    act(() => hook.result.current.recovery.continueInMemory())
    expect(hook.result.current.recovery.memoryOnly).toBe(true)
    await act(async () => {
      await expect(hook.result.current.mutateAsync(submission)).rejects.toThrow('Lost response')
    })
    const id = hook.result.current.recovery.pending?.id
    hook.unmount()
    const resumed = setup(session)
    expect(resumed.result.current.recovery.pending?.id).toBe(id)
    await act(async () => {
      await resumed.result.current.recovery.check()
    })
    await act(async () => {
      await resumed.result.current.recovery.resend()
    })
    const posts = fetcher.mock.calls.filter(([, init]) => init?.method === 'POST')
    expect(posts).toHaveLength(2)
    for (const [, init] of posts) {
      expect(init?.body).toBe(JSON.stringify(submission))
      expect((init?.headers as Record<string, string>)['Idempotency-Key']).toBe(id)
    }
  })
}

it('retains a delivered result identity when removal is denied and can clear it in memory', async () => {
  const session = 'remove-denied'
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => jsonResponse(reply)),
  )
  const hook = setup(session)
  vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
    throw new Error('blocked')
  })
  await act(async () => {
    await hook.result.current.mutateAsync({ ...body, session_id: session })
  })
  const id = hook.result.current.recovery.pending?.id
  expect(id).toBeTruthy()
  expect(hook.result.current.recovery.error).toContain('could not be cleared')
  act(() => hook.result.current.recovery.continueInMemory())
  expect(hook.result.current.recovery.pending?.id).toBe(id)
  act(() => hook.result.current.recovery.clear())
  expect(hook.result.current.recovery.pending).toBeNull()
})

it('does not deliver an old result after switching sessions', async () => {
  let release!: (response: Response) => void
  vi.stubGlobal(
    'fetch',
    vi.fn(
      () =>
        new Promise<Response>((resolve) => {
          release = resolve
        }),
    ),
  )
  const hook = setup()
  let sent!: Promise<unknown>
  await act(async () => {
    sent = hook.result.current.mutateAsync(body).catch((error) => error)
  })
  hook.rerender({ session: 'new-session' })
  await act(async () => {
    release(jsonResponse(reply))
    await sent
  })
  expect(await sent).toBeInstanceOf(Error)
  expect(hook.result.current.recovery.pending).toBeNull()
  expect(sessionStorage.getItem(assessmentRecoveryKey('session'))).not.toBeNull()
})

for (const code of ['assessment_content_changed', 'assessment_content_required']) {
  it(`preserves a definite ${code} rejection across remount and never resends it`, async () => {
    const fetcher = vi.fn(async () => jsonResponse({ error: { code, message: 'Review the question' } }, 409))
    vi.stubGlobal('fetch', fetcher)
    const hook = setup()
    await act(async () => {
      await expect(
        hook.result.current.mutateAsync({ ...body, questionLabel: 'Old question' }),
      ).rejects.toThrow('Review the question')
    })
    expect(hook.result.current.recovery.stale).toBe(true)
    hook.unmount()
    const resumed = setup()
    expect(resumed.result.current.recovery.stale).toBe(true)
    expect(resumed.result.current.recovery.pending?.body).toEqual(body)
    expect(resumed.result.current.recovery.pending?.question).toBe('Old question')
    await act(async () => {
      await resumed.result.current.recovery.resend()
    })
    expect(fetcher).toHaveBeenCalledTimes(1)
    act(() => resumed.result.current.recovery.clear())
    expect(resumed.result.current.recovery.pending).toBeNull()
    resumed.unmount()
    const refreshed = setup()
    expect(refreshed.result.current.recovery.previousAnswer?.body).toEqual(body)
    expect(refreshed.result.current.recovery.previousAnswer?.question).toBe('Old question')
  })
}

for (const code of ['request_conflict', 'assessment_content_changed_during_grading']) {
  it(`does not mistake ${code} for safe pre-claim rejection`, async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse({ error: { code, message: 'Unconfirmed' } }, 409)),
    )
    const hook = setup()
    await act(async () => {
      await expect(hook.result.current.mutateAsync(body)).rejects.toThrow()
    })
    expect(hook.result.current.recovery.stale).toBe(false)
    expect(hook.result.current.recovery.pending?.body).toEqual(body)
  })
}

it('does not discard rejected work if archiving after refresh fails', () => {
  const pending = {
    version: 1,
    id: crypto.randomUUID(),
    endpoint: '/api/assess/attempt',
    body,
    question: 'Old question',
    rejectedContent: true,
  }
  sessionStorage.setItem(assessmentRecoveryKey('session'), JSON.stringify(pending))
  const hook = setup()
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('Full')
  })
  act(() => hook.result.current.recovery.clear())
  expect(hook.result.current.recovery.pending?.id).toBe(pending.id)
  expect(JSON.parse(sessionStorage.getItem(assessmentRecoveryKey('session'))!).body).toEqual(body)
})

it('keeps multiple refreshed answers until each is explicitly dismissed, including a legacy archive', async () => {
  const legacy = {
    version: 1,
    id: crypto.randomUUID(),
    endpoint: '/api/assess/attempt',
    body,
    question: 'Legacy original',
    rejectedContent: true,
  }
  sessionStorage.setItem('assessment-previous-answer:v1:session', JSON.stringify(legacy))
  vi.stubGlobal(
    'fetch',
    vi.fn(async () =>
      jsonResponse({ error: { code: 'assessment_content_changed', message: 'Changed' } }, 409),
    ),
  )
  const hook = setup()
  for (const questionLabel of ['First original', 'Second original']) {
    await act(async () => {
      await expect(hook.result.current.mutateAsync({ ...body, questionLabel })).rejects.toThrow('Changed')
    })
    act(() => hook.result.current.recovery.clear())
  }
  hook.unmount()
  const resumed = setup()
  expect(resumed.result.current.recovery.previousAnswers.map((value) => value.question)).toEqual([
    'Legacy original',
    'First original',
    'Second original',
  ])
  act(() => resumed.result.current.recovery.dismissPrevious(legacy.id))
  expect(resumed.result.current.recovery.previousAnswers.map((value) => value.question)).toEqual([
    'First original',
    'Second original',
  ])
})

it('can archive a rejected answer in explicit page-memory mode when storage is blocked', async () => {
  const session = 'stale-memory-archive'
  const pending = {
    version: 1,
    id: crypto.randomUUID(),
    endpoint: '/api/assess/attempt',
    body: { ...body, session_id: session },
    question: 'Keep in memory',
    rejectedContent: true,
  }
  sessionStorage.setItem(assessmentRecoveryKey(session), JSON.stringify(pending))
  const hook = setup(session)
  vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
    throw new Error('Blocked')
  })
  act(() => hook.result.current.recovery.continueInMemory())
  act(() => hook.result.current.recovery.clear())
  expect(hook.result.current.recovery.pending).toBeNull()
  hook.unmount()
  const resumed = setup(session)
  expect(resumed.result.current.recovery.previousAnswers[0].question).toBe('Keep in memory')
})

it('finishes a staged grade only explicitly and retains identity on content conflict', async () => {
  const id = crypto.randomUUID()
  sessionStorage.setItem(
    assessmentRecoveryKey('session'),
    JSON.stringify({
      version: 1,
      id,
      endpoint: '/api/assess/attempt',
      body,
      question: 'Original',
    }),
  )
  let fail = true
  const fetcher = vi.fn(async (url: string, init?: RequestInit) => {
    if (init?.method === 'POST') {
      expect(url).toBe(`/api/assess/requests/${id}/finish?session_id=session`)
      expect(init.body).toBeUndefined()
      if (fail)
        return jsonResponse(
          { error: { code: 'assessment_content_changed', message: 'Question changed' } },
          409,
        )
      return jsonResponse(reply)
    }
    return jsonResponse({ status: 'grade_ready', result: null })
  })
  vi.stubGlobal('fetch', fetcher)
  const hook = setup()
  await act(async () => {
    await hook.result.current.recovery.finish()
  })
  expect(fetcher).not.toHaveBeenCalled()
  await act(async () => {
    await hook.result.current.recovery.check()
  })
  expect(fetcher).toHaveBeenCalledTimes(1)
  await act(async () => {
    await hook.result.current.recovery.finish()
  })
  expect(hook.result.current.recovery.pending?.id).toBe(id)
  expect(hook.result.current.recovery.stale).toBe(false)
  expect(hook.result.current.recovery.error).toContain('Question changed')
  fail = false
  await act(async () => {
    await hook.result.current.recovery.finish()
  })
  expect(hook.result.current.recovery.lookup?.status).toBe('completed')
  expect(hook.result.current.recovery.pending?.id).toBe(id)
})
