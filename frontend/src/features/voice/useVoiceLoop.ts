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
  const { sessionId, skillId, lang, conversation, textOnly, makeSocket } = opts

  const close = useCallback(() => {
    mic.current?.stop()
    mic.current = null
    player.current.stop()
    if (socket.current && socket.current.readyState <= 1) {
      socket.current.send(JSON.stringify({ type: 'stop' }))
      socket.current.close()
    }
    socket.current = null
    setStatus('idle')
  }, [])

  useEffect(() => {
    const p = player.current
    // playback outlives `done`: stay "speaking" until the last buffer ended
    p.onIdle = () => {
      if (turnDone.current) setStatus((s) => (s === 'speaking' ? 'ready' : s))
    }
    return () => {
      mic.current?.stop()
      p.close()
      socket.current?.close()
    }
  }, [])

  const connect = useCallback(() => {
    if (socket.current) return
    setError(null)
    setStatus('connecting')
    const url = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/voice/ws`
    const ws = makeSocket ? makeSocket(url) : new WebSocket(url)
    ws.binaryType = 'arraybuffer'
    socket.current = ws
    ws.onopen = () => {
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
    }
    ws.onmessage = (ev) => {
      const msg = JSON.parse(String(ev.data)) as VoiceMessage
      switch (msg.type) {
        case 'ready':
          setReady(msg)
          setStatus('ready')
          break
        case 'listening':
          setNothingHeard(false)
          setStatus('listening')
          break
        case 'nothing_heard':
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
          player.current.stop()
          setStatus('ready')
          break
        case 'done':
          setLatency((msg.latency as Record<string, unknown>) ?? null)
          turnDone.current = true
          setStatus(player.current.pending() > 0 ? 'speaking' : 'ready')
          break
        case 'error':
          if (msg.protocol) break // a client-side protocol slip, never shown to the learner
          setError(String(msg.message))
          setStatus(msg.fallback === 'text' ? 'ready' : 'error')
          break
      }
    }
    ws.onerror = () => {
      setError('The voice connection failed. You can keep typing.')
      setStatus('error')
    }
    ws.onclose = () => {
      socket.current = null
      mic.current?.stop()
      mic.current = null
      setStatus((s) => (s === 'error' ? s : 'idle'))
    }
  }, [sessionId, skillId, lang, conversation, textOnly, makeSocket])

  const listen = useCallback(async () => {
    if (!socket.current || mic.current) return // one microphone stream at a time
    try {
      mic.current = await startMic((pcm) => {
        if (socket.current?.readyState === 1) {
          const bytes = new Uint8Array(pcm.byteLength)
          bytes.set(new Uint8Array(pcm.buffer, pcm.byteOffset, pcm.byteLength))
          socket.current.send(bytes.buffer)
        }
      })
      setStatus('listening')
    } catch (e) {
      setError((e as Error).message)
    }
  }, [])

  const stopListening = useCallback(() => {
    mic.current?.stop()
    mic.current = null
    socket.current?.send(JSON.stringify({ type: 'end_of_speech' }))
  }, [])

  const interrupt = useCallback(() => {
    player.current.stop()
    socket.current?.send(JSON.stringify({ type: 'interrupt' }))
  }, [])

  const sendText = useCallback((text: string) => {
    if (!socket.current || !text.trim()) return
    turnDone.current = false
    setTranscript(text)
    setAnswer('')
    setStatus('thinking')
    socket.current.send(JSON.stringify({ type: 'text', text }))
  }, [])

  return {
    status,
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
