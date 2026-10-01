import { useEffect, useRef, useState } from 'react'
import { EditorState } from '@codemirror/state'
import { EditorView, keymap, lineNumbers } from '@codemirror/view'
import { defaultKeymap, history, historyKeymap, indentWithTab, simplifySelection } from '@codemirror/commands'
import { python } from '@codemirror/lang-python'

/**
 * The exercise editor (ADR-0013): CodeMirror 6 with Python indentation, undo history and line
 * numbers, or the plain <textarea> the learner can switch to (also the fallback when CodeMirror
 * cannot mount — the mount is guarded, a failing module load is not). Keyboard escape is a WCAG
 * invariant, not a nicety: Tab indents inside the editor; after Escape the next Tab (or Shift+Tab)
 * leaves it, with no time limit — tab-focus mode stays on until the editor is focused again.
 * The value is owned by the parent:
 * a Reset or a restored draft flows in through `value`, edits flow out through `onChange`.
 * Syntax colouring needs `@codemirror/language` (not an approved package) — the parser still
 * drives indentation.
 */
const theme = EditorView.theme({
  '&': {
    backgroundColor: 'var(--color-card)',
    color: 'var(--color-fg)',
    border: '1px solid var(--color-line)',
    borderRadius: '0.375rem',
    fontSize: '0.875rem',
    minHeight: '14rem',
  },
  '&.cm-focused': { outline: '3px solid var(--color-accent)', outlineOffset: '2px' },
  '.cm-scroller': {
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Consolas, monospace',
    lineHeight: '1.5',
  },
  '.cm-content': { caretColor: 'var(--color-fg)', padding: '0.5rem 0' },
  '.cm-cursor, .cm-dropCursor': { borderLeftColor: 'var(--color-fg)' },
  '.cm-selectionBackground, &.cm-focused .cm-selectionBackground, ::selection': {
    backgroundColor: 'color-mix(in srgb, var(--color-accent) 35%, transparent)',
  },
  '.cm-gutters': {
    backgroundColor: 'var(--color-bg)',
    color: 'var(--color-muted)',
    borderRight: '1px solid var(--color-line)',
  },
})

export function CodeEditor({
  id,
  value,
  onChange,
  plain,
  onPlainFallback,
}: {
  id: string
  value: string
  onChange: (code: string) => void
  /** true → the plain <textarea>; false → CodeMirror */
  plain: boolean
  /** called when CodeMirror could not mount; the parent then renders the plain editor */
  onPlainFallback?: (reason: string) => void
}) {
  if (plain) return <PlainEditor id={id} value={value} onChange={onChange} />
  return <MirrorEditor id={id} value={value} onChange={onChange} onPlainFallback={onPlainFallback} />
}

function MirrorEditor({
  id,
  value,
  onChange,
  onPlainFallback,
}: {
  id: string
  value: string
  onChange: (code: string) => void
  onPlainFallback?: (reason: string) => void
}) {
  const host = useRef<HTMLDivElement>(null)
  const view = useRef<EditorView | null>(null)
  const latest = useRef({ onChange, onPlainFallback })
  useEffect(() => {
    latest.current = { onChange, onPlainFallback }
  })

  useEffect(() => {
    if (!host.current) return
    try {
      const v = new EditorView({
        parent: host.current,
        state: EditorState.create({
          doc: value,
          extensions: [
            lineNumbers(),
            history(),
            python(),
            EditorView.lineWrapping,
            keymap.of([
              {
                key: 'Escape',
                run: (v) => {
                  simplifySelection(v)
                  v.setTabFocusMode(true) // sticky: the next Tab leaves, however long it takes
                  return true
                },
              },
              indentWithTab,
              ...defaultKeymap,
              ...historyKeymap,
            ]),
            EditorView.domEventHandlers({
              focus: (_e, v) => {
                v.setTabFocusMode(false) // back inside: Tab indents again
                return false
              },
            }),
            EditorView.contentAttributes.of({
              'aria-labelledby': `${id}-label`,
              spellcheck: 'false',
              autocorrect: 'off',
              autocapitalize: 'off',
            }),
            EditorView.updateListener.of((u) => {
              if (u.docChanged) latest.current.onChange(u.state.doc.toString())
            }),
            theme,
          ],
        }),
      })
      view.current = v
      return () => {
        v.destroy()
        view.current = null
      }
    } catch (e) {
      latest.current.onPlainFallback?.((e as Error).message)
      return
    }
    // `value` is read once at mount; later external values are synced by the effect below
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  useEffect(() => {
    const v = view.current
    if (!v) return
    const current = v.state.doc.toString()
    if (current !== value) {
      v.dispatch({ changes: { from: 0, to: current.length, insert: value } })
    }
  }, [value])

  return <div id={id} ref={host} className="mt-1" data-testid="code-mirror" />
}

function PlainEditor({
  id,
  value,
  onChange,
}: {
  id: string
  value: string
  onChange: (code: string) => void
}) {
  const [escaped, setEscaped] = useState(false)
  return (
    <textarea
      id={id}
      className="w-full font-mono text-sm border border-line rounded-md p-2 min-h-56 mt-1"
      value={value}
      spellCheck={false}
      onChange={(e) => onChange(e.target.value)}
      onKeyDown={(e) => {
        if (e.key === 'Escape') {
          setEscaped(true)
          return
        }
        if (e.key === 'Tab' && !e.shiftKey && !e.ctrlKey && !e.metaKey && !escaped) {
          e.preventDefault()
          const el = e.currentTarget
          const { selectionStart, selectionEnd } = el
          const next = value.slice(0, selectionStart) + '  ' + value.slice(selectionEnd)
          onChange(next)
          requestAnimationFrame(() => el.setSelectionRange(selectionStart + 2, selectionStart + 2))
        }
        if (e.key !== 'Escape') setEscaped(false)
      }}
    />
  )
}
