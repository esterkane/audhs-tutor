import { useState } from 'react'
import { act, fireEvent, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { axe } from 'vitest-axe'
import { renderApp } from '../../test/utils'
import { VoicePanel } from './VoicePanel'

/** A scriptable stand-in for the browser WebSocket: records what the client sends. */
class FakeSocket {
  static last: FakeSocket | null = null
  readyState = 0
  binaryType = 'blob'
  sent: unknown[] = []
  onopen: (() => void) | null = null
  onmessage: ((ev: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null
  url: string
  constructor(url: string) {
    this.url = url
    FakeSocket.last = this
    setTimeout(() => {
      this.readyState = 1
      this.onopen?.()
    }, 0)
  }
  send(data: unknown) {
    this.sent.push(data)
  }
  close() {
    this.readyState = 3
    this.onclose?.()
  }
  push(msg: unknown) {
    this.onmessage?.({ data: JSON.stringify(msg) })
  }
}

const makeSocket = (url: string) => new FakeSocket(url) as unknown as WebSocket

describe('VoicePanel', () => {
  afterEach(() => vi.restoreAllMocks())

  it('connects only on click, sends start, shows transcript + streamed answer, interrupts, and types as fallback', async () => {
    const { container } = renderApp(<VoicePanel sessionId="s1" skillId="k1" makeSocket={makeSocket} />)
    expect(FakeSocket.last).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Connect' }))
    await waitFor(() => expect(FakeSocket.last?.sent).toHaveLength(1))
    const ws = FakeSocket.last!
    expect(JSON.parse(String(ws.sent[0]))).toMatchObject({
      type: 'start',
      session_id: 's1',
      skill_id: 'k1',
      conversation: false,
    })
    act(() => ws.push({ type: 'ready', stt: 'fake-stt', tts: 'fake-tts', vad: 'energy', text_only: false }))
    expect(await screen.findByText('Ready')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Talk' })).toBeInTheDocument()
    act(() => ws.push({ type: 'listening' }))
    act(() => ws.push({ type: 'transcript', text: 'what is attention', language: 'en' }))
    expect(screen.getByText(/You said:/).closest('p')).toHaveTextContent('what is attention')
    act(() => ws.push({ type: 'token', text: 'Attention ' }))
    act(() => ws.push({ type: 'token', text: 'weighs tokens.' }))
    expect(screen.getByText(/Attention weighs tokens\./)).toBeInTheDocument()
    act(() => ws.push({ type: 'audio', pcm16_b64: 'AAAA', sample_rate: 24000 }))
    expect(screen.getByText(/Speaking — press Interrupt/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Interrupt' }))
    expect(JSON.parse(String(ws.sent[ws.sent.length - 1]))).toEqual({ type: 'interrupt' })
    act(() => ws.push({ type: 'interrupted' }))
    act(() =>
      ws.push({
        type: 'done',
        turn: { turn_id: 't1', answer_id: 'saved-1', text: 'Canonical saved explanation.' },
        latency: { total_ms: 812, tts_first_audio_ms: 400, interrupted: true },
      }),
    )
    expect(screen.queryByText(/812 ms/)).not.toBeInTheDocument() // telemetry stays out of the learning screen
    expect(screen.getByText('Saved to your local answer history.')).toBeInTheDocument()
    expect(screen.queryByText('Canonical saved explanation.')).not.toBeInTheDocument()
    expect(screen.getByText(/Saved-answer status refers to the completed response/)).toBeVisible()
    expect(screen.getByText('Attention weighs tokens.')).toBeInTheDocument()
    // protocol slips never reach the learner
    act(() => ws.push({ type: 'error', message: 'not JSON', protocol: true }))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(await axe(container)).toHaveNoViolations()
    // text-only fallback in the same conversation
    fireEvent.change(screen.getByLabelText('Type instead'), { target: { value: 'and shorter?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    expect(JSON.parse(String(ws.sent[ws.sent.length - 1]))).toEqual({ type: 'text', text: 'and shorter?' })
    expect(screen.getByText(/You said:/).closest('p')).toHaveTextContent('and shorter?')
    expect(screen.queryByText('Saved to your local answer history.')).not.toBeInTheDocument()
    // stop closes the socket after a stop message
    fireEvent.click(screen.getByRole('button', { name: 'Stop voice' }))
    expect(JSON.parse(String(ws.sent[ws.sent.length - 1]))).toEqual({ type: 'stop' })
    expect(ws.readyState).toBe(3)
  })

  it('explains a missing microphone and keeps typing available; text-only mode hides Talk', async () => {
    renderApp(<VoicePanel sessionId="s1" makeSocket={makeSocket} />)
    fireEvent.click(screen.getByRole('button', { name: 'Connect' }))
    await waitFor(() => expect(FakeSocket.last?.sent).toHaveLength(1))
    const ws = FakeSocket.last!
    act(() => ws.push({ type: 'ready', stt: 'fake-stt', tts: 'fake-tts', vad: 'energy', text_only: false }))
    // jsdom has no getUserMedia
    fireEvent.click(await screen.findByRole('button', { name: 'Talk' }))
    expect(await screen.findByRole('alert')).toHaveTextContent(/no microphone access/)
    expect(screen.getByLabelText('Type instead')).toBeInTheDocument()
    // a server-side fallback keeps the panel usable
    act(() =>
      ws.push({
        type: 'error',
        message: 'The speech recogniser did not answer. Type your question instead.',
        fallback: 'text',
      }),
    )
    expect(screen.getByRole('alert')).toHaveTextContent(/Type your question instead/)
    act(() => ws.push({ type: 'nothing_heard' }))
    expect(screen.getByText(/Nothing heard/)).toBeInTheDocument()
    // text-only readiness → no Talk button
    act(() => ws.close())
    fireEvent.click(await screen.findByRole('button', { name: 'Reconnect' }))
    await waitFor(() => expect(FakeSocket.last).not.toBe(ws))
    act(() =>
      FakeSocket.last!.push({
        type: 'ready',
        stt: null,
        tts: null,
        vad: 'energy',
        text_only: true,
        why_text_only: 'speech components not ready',
      }),
    )
    expect(await screen.findByText(/Text only \(speech components not ready\)/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Talk' })).not.toBeInTheDocument()
  })
})

it('keeps an unsent draft visible after send failure, Stop and reconnect', async () => {
  const onClose = vi.fn()
  renderApp(<VoicePanel sessionId="s1" makeSocket={makeSocket} onClose={onClose} />)
  fireEvent.change(screen.getByLabelText('Type instead'), { target: { value: 'Keep my question' } })
  expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
  fireEvent.click(screen.getByRole('button', { name: 'Connect' }))
  await waitFor(() => expect(FakeSocket.last?.sent).toHaveLength(1))
  const ws = FakeSocket.last!
  act(() => ws.push({ type: 'ready' }))
  vi.spyOn(ws, 'send').mockImplementation(() => {
    throw new Error('closed')
  })
  fireEvent.click(screen.getByRole('button', { name: 'Send' }))
  expect(screen.getByLabelText('Type instead')).toHaveValue('Keep my question')
  expect(screen.getByRole('alert')).toHaveTextContent('not sent')
  fireEvent.click(screen.getByRole('button', { name: 'Stop voice' }))
  expect(screen.getByLabelText('Type instead')).toHaveValue('Keep my question')
  expect(onClose).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: 'Connect' }))
  await waitFor(() => expect(FakeSocket.last).not.toBe(ws))
  act(() => FakeSocket.last!.push({ type: 'ready' }))
  expect(screen.getByLabelText('Type instead')).toHaveValue('Keep my question')
})

it('Stop retains text with a real unmounting owner; only Clear and close removes the panel', () => {
  function Owner() {
    const [open, setOpen] = useState(true)
    return open ? (
      <VoicePanel sessionId="s" makeSocket={makeSocket} onClose={() => setOpen(false)} />
    ) : (
      <p>Panel closed</p>
    )
  }
  renderApp(<Owner />)
  fireEvent.change(screen.getByLabelText('Type instead'), { target: { value: 'unsent' } })
  fireEvent.click(screen.getByRole('button', { name: 'Connect' }))
  fireEvent.click(screen.getByRole('button', { name: 'Stop voice' }))
  expect(screen.getByLabelText('Type instead')).toHaveValue('unsent')
  fireEvent.click(screen.getByRole('button', { name: 'Clear and close panel' }))
  expect(screen.getByText('Panel closed')).toBeVisible()
})

it('offers save-only recovery for a completed voice answer', async () => {
  const fetcher = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
    new Response(JSON.stringify({ answer_id: 'voice-saved' }), {
      headers: { 'Content-Type': 'application/json' },
    }),
  )
  renderApp(<VoicePanel sessionId="s1" makeSocket={makeSocket} />)
  fireEvent.click(screen.getByRole('button', { name: 'Connect' }))
  await waitFor(() => expect(FakeSocket.last?.sent).toHaveLength(1))
  act(() =>
    FakeSocket.last!.push({
      type: 'done',
      turn: {
        turn_id: 'voice-turn',
        outcome: 'ok',
        text: 'Completed voice explanation.',
        save_error: 'Save failed',
        save_receipt: 'voice-receipt',
      },
    }),
  )
  expect(screen.getByText('Completed voice explanation.')).toBeVisible()
  fireEvent.click(screen.getByRole('button', { name: 'Retry saving' }))
  expect(await screen.findByRole('link', { name: 'Open saved answer' })).toHaveAttribute(
    'href',
    '/answers/voice-saved',
  )
  expect(fetcher).toHaveBeenCalledWith(
    '/api/answers/recover-save',
    expect.objectContaining({ body: JSON.stringify({ receipt: 'voice-receipt' }) }),
  )
  expect(FakeSocket.last!.sent).toHaveLength(1)
  fetcher.mockRestore()
})
