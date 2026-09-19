import type { components } from './api-types'

export type Schemas = components['schemas']
export type SessionOut = Schemas['SessionOut']
export type SkillView = Schemas['SkillView']
export type SkillList = Schemas['SkillList']
export type TurnDone = Schemas['TurnDone']
export type TurnRequest = Omit<Schemas['TurnRequest'], 'action'> & {
  action?: Schemas['TurnRequest']['action']
}
/** Emitted on the SSE stream only (not part of the OpenAPI response models). */
export type TurnMeta = {
  turn_id: string
  session_id: string
  skill_id: string
  skill_title: string
  action: string
  hint_level: number
  prompt_version: string
  questioning_style: string
}
export type AssessmentView = Schemas['AssessmentView']
export type NextItem = Schemas['NextItem']
export type AttemptRequest = Schemas['AttemptRequest']
export type AttemptResult = Schemas['AttemptResult']
export type DueList = Schemas['DueList']
export type ReviewItemOut = Schemas['ReviewItemOut']
export type ReviewOut = Schemas['ReviewOut']
export type ParkOut = Schemas['ParkOut']
export type LearnerOut = Schemas['LearnerOut']

export class ApiError extends Error {
  status: number
  code: string
  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  if (!res.ok) {
    let code = 'http_error'
    let message = res.statusText
    try {
      const body = (await res.json()) as {
        error?: { code: string; message: string }
        detail?: unknown
      }
      if (body.error) {
        code = body.error.code
        message = body.error.message
      } else if (body.detail) {
        message = JSON.stringify(body.detail)
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, code, message)
  }
  return (await res.json()) as T
}

export const api = {
  me: () => apiFetch<LearnerOut>('/api/learner/me'),
  skills: () => apiFetch<SkillList>('/api/skills'),
  startSession: (body: { mode: string; energy: number; socratic: boolean }) =>
    apiFetch<SessionOut>('/api/sessions', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  session: (id: string) => apiFetch<SessionOut>(`/api/sessions/${id}`),
  endSession: (id: string, body: { energy_after: number; self_report: number; notes?: string }) =>
    apiFetch<SessionOut>(`/api/sessions/${id}/end`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  nextItem: (sessionId: string, skillId?: string) =>
    apiFetch<NextItem>(
      `/api/assess/next?session_id=${encodeURIComponent(sessionId)}${skillId ? `&skill_id=${encodeURIComponent(skillId)}` : ''}`,
    ),
  attempt: (body: AttemptRequest) =>
    apiFetch<AttemptResult>('/api/assess/attempt', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  due: (sessionId: string, all = false) =>
    apiFetch<DueList>(`/api/review/due?session_id=${encodeURIComponent(sessionId)}${all ? '&all=true' : ''}`),
  rate: (
    itemId: string,
    body: { session_id: string; rating: number; latency_ms?: number; confidence_pre?: number },
  ) =>
    apiFetch<ReviewOut>(`/api/review/${itemId}`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  park: (body: { session_id: string | null; text: string; node_id?: string | null }) =>
    apiFetch<ParkOut>('/api/parking', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  parked: () => apiFetch<{ items: ParkOut[] }>('/api/parking'),
}

export type StreamHandlers = {
  onMeta?: (m: TurnMeta) => void
  onToken?: (t: string) => void
  onDone?: (d: TurnDone) => void
  onError?: (e: { code: string; message: string }) => void
}

/** Consume the SSE tutor stream (fetch + ReadableStream; EventSource cannot POST). */
export async function streamTurn(body: TurnRequest, h: StreamHandlers, signal?: AbortSignal): Promise<void> {
  const res = await fetch('/api/tutor/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
    signal,
  })
  if (!res.ok || !res.body) {
    h.onError?.({
      code: 'http_error',
      message: `${res.status} ${res.statusText}`,
    })
    return
  }
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let idx: number
    while ((idx = buffer.indexOf('\n\n')) >= 0) {
      const block = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      dispatch(block, h)
    }
  }
  if (buffer.trim()) dispatch(buffer, h)
}

function dispatch(block: string, h: StreamHandlers) {
  let event = 'message'
  let data = ''
  for (const line of block.split('\n')) {
    if (line.startsWith('event: ')) event = line.slice(7)
    else if (line.startsWith('data: ')) data += line.slice(6)
  }
  if (!data) return
  const payload = JSON.parse(data)
  if (event === 'meta') h.onMeta?.(payload as TurnMeta)
  else if (event === 'token') h.onToken?.((payload as { text: string }).text)
  else if (event === 'done') h.onDone?.(payload as TurnDone)
  else if (event === 'error') h.onError?.(payload as { code: string; message: string })
}
