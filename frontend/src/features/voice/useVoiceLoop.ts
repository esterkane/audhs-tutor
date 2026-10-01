import { useCallback, useEffect, useRef, useState } from 'react'
import { b64ToPcm16, Player, startMic, type Mic } from './audio'

export type VoiceStatus = 'idle' | 'connecting' | 'ready' | 'listening' | 'thinking' | 'speaking' | 'error'
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
  makeSocket?: (url: string) => WebSocket
}) {
  const [status, setStatus] = useState<VoiceStatus>('idle')
  const [ready, setReady] = useState<VoiceMessage | null>(null)
  const [transcript, setTranscript] = useState('')
  const [answer, setAnswer] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [latency, setLatency] = useState<Record<string, unknown> | null>(null)
  const [nothingHeard, setNothingHeard] = useState(false)
  const socket = useRef<WebSocket | null>(null)
  const mic = useRef<Mic | null>(null)
  const player = useRef(new Player())
  const turnDone = useRef(false)
  const handshake = useRef(false)
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
      switch (msg.type) {
        case 'ready':
          turnBusy.current = false
          clearTimer()
          handshake.current = true
          setReady(msg)
          setError(null)
          setStatus('ready')
          break
        case 'listening':
          setNothingHeard(false)
          setStatus('listening')
          break
        case 'nothing_heard':
          turnBusy.current = false
          setNothingHeard(true)
          setStatus('ready')
          break
        case 'transcript':
          turnDone.current = false
          setTranscript(String(msg.text))
          setAnswer('')
          setStatus('thinking')
          break
        case 'token':
          setAnswer((a) => a + String(msg.text))
          break
        case 'audio':
          setStatus('speaking')
          player.current.enqueue(b64ToPcm16(String(msg.pcm16_b64)), Number(msg.sample_rate))
          break
        case 'interrupted':
          turnBusy.current = false
          player.current.stop()
          setStatus('ready')
          break
        case 'done':
          turnBusy.current = false
          setLatency((msg.latency as Record<string, unknown>) ?? null)
          turnDone.current = true
          setStatus(player.current.pending() > 0 ? 'speaking' : 'ready')
          break
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
    player.current.stop()
    sendControl('interrupt')
  }, [sendControl])
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
      try {
        ws.send(JSON.stringify({ type: 'text', text }))
      } catch {
        setError('Your message was not sent. The draft is kept; reconnect to try again.')
        setStatus('error')
        return false
      }
      turnBusy.current = true
      turnDone.current = false
      setTranscript(text)
      setAnswer('')
      setError(null)
      setStatus('thinking')
      return true
    },
    [status],
  )

  return {
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
