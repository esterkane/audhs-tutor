import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Button } from './ui/button'

/** Navigation only: opening this dialog never changes a learning checkpoint. */
export function QuickNavigation({ pages }: { pages: ReadonlyArray<readonly [string, string]> }) {
  const dialog = useRef<HTMLDialogElement>(null)
  const input = useRef<HTMLInputElement>(null)
  const previousFocus = useRef<HTMLElement | null>(null)
  const [query, setQuery] = useState('')
  const navigate = useNavigate()
  const location = useLocation()
  function open() {
    if (dialog.current?.open || document.querySelector('dialog[open], [role="dialog"][aria-modal="true"]')) return
    previousFocus.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
    setQuery('')
    dialog.current?.showModal()
    input.current?.focus()
  }
  function close(restore = true) {
    dialog.current?.close()
    if (restore && previousFocus.current?.isConnected) previousFocus.current.focus()
  }
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.defaultPrevented || event.isComposing || event.repeat || event.altKey || event.shiftKey || !(event.metaKey || event.ctrlKey) || event.key.toLowerCase() !== 'k') return
      const target = event.target instanceof HTMLElement ? event.target : null
      // Leave editor/input shortcuts and other modal work alone.
      if (target?.closest('input, textarea, select, [contenteditable="true"], .cm-editor, [role="textbox"]')) return
      if (document.querySelector('dialog[open], [role="dialog"][aria-modal="true"]')) return
      event.preventDefault()
      open()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])
  useEffect(() => { dialog.current?.close() }, [location.key])
  const phrase = query.trim()
  const matching = pages.filter(([, title]) => title.toLocaleLowerCase().includes(phrase.toLocaleLowerCase()))
  return <>
    <Button variant="outline" aria-haspopup="dialog" aria-keyshortcuts="Control+k Meta+k" onClick={open}>Search or go to</Button>
    <dialog ref={dialog} aria-labelledby="quick-navigation-title" aria-describedby="quick-navigation-help"
      className="m-auto w-full max-w-lg max-h-[85dvh] overflow-hidden rounded-lg border border-line bg-card text-fg p-0 backdrop:bg-fg/30"
      onCancel={event => { event.preventDefault(); close() }}
      onKeyDown={event => { if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close() } }}>
      <div className="flex max-h-[85dvh] flex-col">
      <div className="shrink-0 border-b border-line p-4 flex flex-wrap items-center justify-between gap-2">
        <h2 id="quick-navigation-title" className="text-lg font-semibold">Search or go to</h2>
        <Button onClick={() => close()}>Close</Button>
      </div>
      <div className="min-h-0 overflow-y-auto p-4">
      <p id="quick-navigation-help" className="text-sm text-muted my-2">Search knowledge areas, saved explanations and indexed sources, or choose a page. Escape returns to your current work. Shortcut: Ctrl/Cmd+K outside text editors.</p>
      <form className="grid gap-2" onSubmit={event => {
        event.preventDefault()
        close(false)
        navigate(`/search${phrase ? `?${new URLSearchParams({ q: phrase })}` : ''}`)
        document.getElementById('main-content')?.focus()
      }}>
        <label>Search phrase or page name
          <input ref={input} type="search" maxLength={200} value={query} onChange={event => setQuery(event.target.value)} className="block w-full min-w-0 min-h-10 rounded-md border border-control bg-card px-3 py-2 mt-1" />
        </label>
        <Button type="submit">{phrase ? 'Search material for this phrase' : 'Open material search'}</Button>
      </form>
      <h3 className="font-semibold mt-4">Go to a page</h3>
      {!matching.length && <p role="status">No page names match. You can still search material above.</p>}
      <ul className="grid gap-2 mt-2">{matching.map(([path, title]) => <li key={path}><Link className="inline-block underline py-1" to={path} onClick={event => {
        if (!event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
          close(false)
          document.getElementById('main-content')?.focus()
        }
      }}>{title}</Link></li>)}</ul>
      </div>
      </div>
    </dialog>
  </>
}
