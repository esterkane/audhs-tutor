import { useContext, useRef } from 'react'
import { Button } from '../../components/ui/button'
import { useReadingControls } from '../voice/readingOwner'
import { requestGeneralCapture } from '../parking/requestCapture'

import { LessonFocusContext } from './focusContext'

/** Presentation only: existing audio and saved-thought owners perform every action. */
export function LessonFocusControls() {
  const focus = useContext(LessonFocusContext)
  const reading = useReadingControls(s => s.reading)
  const toggle = useRef<HTMLButtonElement | null>(null)
  if (!focus) return null
  return <>
    <Button data-focus-toggle onClick={event => { toggle.current = event.currentTarget; focus.setActive(!focus.active) }} aria-pressed={focus.active}>
      {focus.active ? 'Leave focus · Esc' : 'Focus on lesson'}
    </Button>
    {focus.active && <>
      <Button data-focus-only onClick={event => requestGeneralCapture(event.currentTarget)}>Save for later</Button>
      {reading && <div data-focus-only className="basis-full text-sm">
        <p>{reading.status}</p>
        <Button onClick={() => { reading.stop(); toggle.current?.focus() }}>Stop audio</Button>
      </div>}
    </>}
  </>
}
