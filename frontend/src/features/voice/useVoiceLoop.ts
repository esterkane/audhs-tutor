import type { TurnDone } from '../../lib/api'
import { useCallback, useEffect, useRef, useState } from 'react'
import { b64ToPcm16, Player, startMic, type Mic } from './audio'

export type VoiceStatus =
  'idle' | 'connecting' | 'ready' | 'listening' | 'thinking' | 'speaking' | 'stopping' | 'error'
export type VoiceMessage = { type: string; [k: string]: unknown }

/**
 * One WebSocket voice conversation. Nothing starts without `connect()` (a click); the microphone
 * opens only on `startMic`; playback only for audio the server sends for this turn; `interrupt()`
 * stops playback and the current turn; the transcript and the answer text are always visible, and
 * `sendText` is the text-only fallback for the same conversation.
 */
export function useVoiceLoop(opts: {
  sessionId: string
  skillId?: string | null
  lang?: string | null
  conversation?: boolean
  textOnly?: boolean
  initialText?: { transcript: string; answer: string; interrupted: boolean }
  makeSocket?: (url: string) => WebSocket
}) {
  const [status, setStatus] = useState<VoiceStatus>('idle')
  const [ready, setReady] = useState<VoiceMessage | null>(null)
  const [transcript, setTranscript] = useState(opts.initialText?.transcript ?? '')
  const [answer, setAnswer] = useState(opts.initialText?.answer ?? '')
  const [saveTurn, setSaveTurn] = useState<Pick<
    TurnDone,
    'turn_id' | 'text' | 'answer_id' | 'save_error' | 'save_receipt'
  > | null>(null)
  const [saveNote, setSaveNote] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [latency, setLatency] = useState<Record<string, unknown> | null>(null)
  const [nothingHeard, setNothingHeard] = useState(false)
  const [interrupted, setInterrupted] = useState(opts.initialText?.interrupted ?? false)
  const socket = useRef<WebSocket | null>(null)
  const mic = useRef<Mic | null>(null)
  const player = useRef(new Player())
  const interruptedTurn = useRef(false)
  const interruptAck = useRef(false)
  const interruptTerminal = useRef(false)
  const turnDone = useRef(false)
  const handshake = useRef(false)
  const identifiedText = useRef(false)
  const requestIdentity = useRef<string | null>(null)
  const turnBusy = useRef(false)
  const micGeneration = useRef(0)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const clearTimer = () => {
    if (timer.current) clearTimeout(timer.current)
    timer.current = null
  }

  const { sessionId, skillId, lang, conversation, textOnly, makeSocket } = opts

  const close = useCallback(() => {
    clearTimer()
    micGeneration.current++
    mic.current?.stop()
    mic.current = null
    player.current.stop()
    const ws = socket.current
    socket.current = null
    handshake.current = false
    if (ws) {
      try {
        if (ws.readyState === 1) ws.send(JSON.stringify({ type: 'stop' }))
      } catch {
        /* disconnected */
      }
      try {
        ws.close()
      } catch {
        /* already closed */
      }
    }
    setReady(null)
    setStatus('idle')
  }, [])

  useEffect(() => {
    const p = player.current
    // playback outlives `done`: stay "speaking" until the last buffer ended
    p.onIdle = () => {
      if (turnDone.current) setStatus((s) => (s === 'speaking' ? 'ready' : s))
    }
    return () => {
      clearTimer()
      // Clearing socket ownership below also invalidates pending microphone acquisition.
      mic.current?.stop()
      p.close()
      const ws = socket.current
      socket.current = null
      handshake.current = false
      ws?.close()
    }
  }, [])

  const connect = useCallback(() => {
    if (socket.current) return
    identifiedText.current = false
    requestIdentity.current = null
    setError(null)
    setStatus('connecting')
    const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/voice/ws`
    handshake.current = false
    setReady(null)
    let ws: WebSocket
    try {
      ws = makeSocket ? makeSocket(url) : new WebSocket(url)
    } catch {
      setError('Could not connect. Your draft is kept; reconnect to send.')
      setStatus('error')
      return
    }
    ws.binaryType = 'arraybuffer'
    socket.current = ws
    const current = () => socket.current === ws
    const fail = (message: string) => {
      if (!current()) return
      clearTimer()
      socket.current = null
      handshake.current = false
      micGeneration.current++
      mic.current?.stop()
      mic.current = null
      player.current.stop()
      try {
        ws.close()
      } catch {
        /* already disconnected */
      }
      setError(message)
      setStatus('error')
    }
    timer.current = setTimeout(
      () => fail('Connection timed out. Your draft is kept; reconnect to send.'),
      15000,
    )
    ws.onopen = () => {
      if (!current() || ws.readyState !== 1) return
      try {
        ws.send(
          JSON.stringify({
            type: 'start',
            session_id: sessionId,
            skill_id: skillId ?? null,
            lang: lang ?? null,
            conversation: !!conversation,
            text_only: !!textOnly,
          }),
        )
      } catch {
        fail('Could not start the connection. Reconnect to send.')
      }
    }
    ws.onmessage = (ev) => {
      if (!current()) return
      let msg: VoiceMessage
      try {
        msg = JSON.parse(String(ev.data)) as VoiceMessage
        if (!msg || typeof msg.type !== 'string') throw new Error()
      } catch {
        fail('The voice connection returned an unreadable response. Reconnect to send.')
        return
      }
      if (
        identifiedText.current &&
        ['transcript', 'meta', 'token', 'audio', 'done', 'error'].includes(msg.type) &&
        !msg.protocol
      ) {
        if (
          (requestIdentity.current !== null || msg.request_id !== undefined) &&
          msg.request_id !== requestIdentity.current
        )
          return
      }
      if (interruptedTurn.current && msg.type === 'error' && !msg.protocol) {
        fail('The interrupted turn could not finish. Received text is kept; reconnect when ready.')
        return
      }
      // The server acknowledges interruption before its trace/TTS cleanup finishes.
      // Keep that turn fenced until done; neither queued audio nor final text may replace it.
      if (interruptedTurn.current && ['transcript', 'meta', 'token', 'audio'].includes(msg.type)) return
      switch (msg.type) {
        case 'ready':
          identifiedText.current = msg.request_identity === 'typed-v1'
          requestIdentity.current = null
          turnBusy.current = false
          clearTimer()
          handshake.current = true
          setReady(msg)
          setError(null)
          setStatus('ready')
          break
        case 'listening':
          if (interruptedTurn.current) break
          setNothingHeard(false)
          setStatus('listening')
          break
        case 'nothing_heard':
          if (interruptedTurn.current) {
            interruptTerminal.current = true
            if (!interruptAck.current) break
          }
          clearTimer()
          turnBusy.current = false
          setNothingHeard(true)
          setStatus('ready')
          break
        case 'transcript':
          turnDone.current = false
          setTranscript(String(msg.text))
          setAnswer('')
          setSaveNote(null)
          setSaveTurn(null)
          setStatus('thinking')
          break
        case 'meta':
          setSaveNote(null)
          setSaveTurn(null)
          break
        case 'token':
          setAnswer((a) => a + String(msg.text))
          break
        case 'audio':
          setStatus('speaking')
          player.current.enqueue(b64ToPcm16(String(msg.pcm16_b64)), Number(msg.sample_rate))
          break
        case 'interrupted':
          if (interruptedTurn.current) {
            interruptAck.current = true
            if (!interruptTerminal.current) break
            clearTimer()
          }
          turnBusy.current = false
          player.current.stop()
          setStatus('ready')
          break
        case 'done': {
          const turn = msg.turn as {
            turn_id?: string
            outcome?: string
            save_receipt?: string | null
            answer_id?: string | null
            save_error?: string | null
            text?: string
          } | null
          interruptTerminal.current = true
          if (!interruptedTurn.current || interruptAck.current) clearTimer()
          if (!interruptedTurn.current && typeof turn?.text === 'string') setAnswer(turn.text)
          setSaveTurn(
            turn?.outcome !== 'partial' && typeof turn?.turn_id === 'string' && typeof turn.text === 'string'
              ? {
                  turn_id: turn.turn_id,
                  text: turn.text,
                  answer_id: turn.answer_id,
                  save_error: turn.save_error,
                  save_receipt: turn.save_receipt,
                }
              : null,
          )
          setSaveNote(turn?.save_error ?? (turn?.answer_id ? 'Saved to your local answer history.' : null))
          turnBusy.current = interruptedTurn.current && !interruptAck.current
          setLatency((msg.latency as Record<string, unknown>) ?? null)
          turnDone.current = true
          setStatus(turnBusy.current ? 'stopping' : player.current.pending() > 0 ? 'speaking' : 'ready')
          break
        }
        case 'error':
          if (msg.protocol) break // a client-side protocol slip, never shown to the learner
          if (msg.fallback === 'text') {
            turnBusy.current = false
            setError(String(msg.message))
            setStatus('ready')
          } else {
            fail(String(msg.message))
          }
          break
      }
    }
    ws.onerror = () => fail('The connection failed. Your draft is kept; reconnect to send it.')
    ws.onclose = () => {
      if (!current()) return
      fail('The connection closed. Your draft is kept; reconnect to send it.')
    }
  }, [sessionId, skillId, lang, conversation, textOnly, makeSocket])

  const listen = useCallback(async () => {
    const ws = socket.current
    if (
      !ws ||
      ws.readyState !== 1 ||
      !handshake.current ||
      mic.current ||
      turnBusy.current ||
      status !== 'ready'
    )
      return
    requestIdentity.current = null
    interruptedTurn.current = false
    setInterrupted(false)
    turnDone.current = false
    player.current.stop() // explicit new response boundary, including delayed audio chunks
    turnBusy.current = true
    const generation = ++micGeneration.current
    setStatus('listening')
    try {
      const opened = await startMic((pcm) => {
        if (socket.current === ws && ws.readyState === 1 && micGeneration.current === generation) {
          const bytes = new Uint8Array(pcm.byteLength)
          bytes.set(new Uint8Array(pcm.buffer, pcm.byteOffset, pcm.byteLength))
          try {
            ws.send(bytes.buffer)
          } catch {
            setError('Audio could not be sent. Stop and reconnect.')
          }
        }
      })
      if (socket.current !== ws || ws.readyState !== 1 || micGeneration.current !== generation) {
        opened.stop()
        return
      }
      mic.current = opened
    } catch (e) {
      if (socket.current === ws && micGeneration.current === generation) {
        turnBusy.current = false
        setError((e as Error).message)
        setStatus('ready')
      }
    }
  }, [status])
  const sendControl = useCallback((type: string) => {
    const ws = socket.current
    if (ws?.readyState !== 1) return false
    try {
      ws.send(JSON.stringify({ type }))
      return true
    } catch {
      return false
    }
  }, [])
  const stopListening = useCallback(() => {
    micGeneration.current++
    mic.current?.stop()
    mic.current = null
    if (!sendControl('end_of_speech')) {
      setError('Disconnected. Your draft is kept; reconnect to send.')
      setStatus('error')
    } else setStatus('thinking')
  }, [sendControl])
  const interrupt = useCallback(() => {
    interruptedTurn.current = true
    interruptAck.current = false
    interruptTerminal.current = false
    setInterrupted(true)
    player.current.stop()
    // Playback may still be draining after a completed server turn.
    if (turnDone.current) {
      setStatus('ready')
      return
    }
    turnBusy.current = true
    setStatus('stopping')
    const failed = () => {
      close()
      setError('The interrupted turn did not finish. Received text is kept; reconnect when ready.')
      setStatus('error')
    }
    if (!sendControl('interrupt')) {
      failed()
      return
    }
    clearTimer()
    timer.current = setTimeout(failed, 15000)
  }, [sendControl, close])
  const sendText = useCallback(
    (text: string) => {
      const ws = socket.current
      if (
        !ws ||
        ws.readyState !== 1 ||
        !handshake.current ||
        turnBusy.current ||
        status !== 'ready' ||
        !text.trim()
      )
        return false
      const identity = identifiedText.current ? crypto.randomUUID() : null
      try {
        ws.send(JSON.stringify({ type: 'text', text, ...(identity ? { request_id: identity } : {}) }))
      } catch {
        setError('Your message was not sent. The draft is kept; reconnect to try again.')
        setStatus('error')
        return false
      }
      requestIdentity.current = identity
      interruptedTurn.current = false
      setInterrupted(false)
      player.current.stop()
      turnBusy.current = true
      turnDone.current = false
      setTranscript(text)
      setAnswer('')
      setSaveNote(null)
      setSaveTurn(null)
      setError(null)
      setStatus('thinking')
      return true
    },
    [status],
  )

  return {
    interrupted,
    saveNote,
    saveTurn,
    status,
    canSend: status === 'ready',
    ready,
    transcript,
    answer,
    error,
    latency,
    nothingHeard,
    connect,
    listen,
    stopListening,
    interrupt,
    sendText,
    close,
  }
}
