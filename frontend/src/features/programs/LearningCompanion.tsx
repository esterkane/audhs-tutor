import { useState } from 'react'
import { Button } from '../../components/ui/button'
import { ReadAloud } from '../voice/ReadAloud'
import { StudyTutor } from './StudyTutor'

/** Context is captured only on explicit click; no continuous page monitoring. */
export function LearningCompanion() {
  const [passage, setPassage] = useState('')
  const [open, setOpen] = useState(false)
  return (
    <section aria-label="Learning companion" className="border-t border-line p-4 max-w-3xl mx-auto">
      <Button
        variant="outline"
        onClick={() => {
          const selection = window.getSelection()?.toString().trim() ?? ''
          setPassage(selection || document.querySelector('main')?.innerText.trim().slice(0, 12000) || '')
          setOpen(true)
        }}
      >
        Listen or ask about this page
      </Button>
      {open && (
        <div className="grid gap-3 mt-3">
          <p>
            Select a passage before opening for focused help, or edit the captured text below. Only this text
            is shared when you send a tutor request.
          </p>
          <label>
            Material to discuss
            <textarea
              className="block w-full bg-card border rounded p-2"
              value={passage}
              onChange={(e) => setPassage(e.target.value)}
            />
          </label>
          <ReadAloud key={passage} text={passage} />
          <StudyTutor key={passage} context={passage} />
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Close learning companion
          </Button>
        </div>
      )}
    </section>
  )
}
