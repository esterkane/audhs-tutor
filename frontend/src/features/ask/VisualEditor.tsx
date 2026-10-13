import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '../../components/ui/button'
import { Disclosure } from '../../components/ui/disclosure'
import type { Schemas } from '../../lib/api'
import { boundedRead } from '../../lib/boundedRead'
import { useLessonDraft } from '../tutor/useLessonDraft'
import { RequestRecoveryControls } from '../playground/RequestRecoveryControls'
import { useVisualSaveRecovery, type PendingTutorRequest } from '../playground/useRequestRecovery'
import { VisualFallback } from '../visual-learning/VisualFallback'
import { editableFields, restoreVisualEdit, validVisualEdits, visualSaveBody, type VisualEdits, type VisualEditDraft } from './visualEditing'
const RelationshipGraph = lazy(() => import('../visual-learning/RelationshipGraph'))
const field = 'block w-full rounded border border-line bg-card p-2'
type Document = Schemas['VisualDocumentSummary']

export function VisualEditor({ document, version, learnerId, readOnly }: { document: Document; version: Schemas['VisualVersionDetail']; learnerId: string; readOnly: boolean }) {
  const scope = `visual-edit:${learnerId}:${document.id}:${version.id}`
  const stored = useLessonDraft(scope, 'diagram edit')
  const recovery = useVisualSaveRecovery(scope, document.id, version)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState('')
  const [preview, setPreview] = useState(false)
  const [undo, setUndo] = useState<VisualEdits[]>([])
  const [comparison, setComparison] = useState<Schemas['VisualVersionDetail'] | null>(null)
  const active = useRef<AbortController | null>(null)
  const mounted = useRef(true)
  const cache = useQueryClient()
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; active.current?.abort() } }, [])
  let draft: VisualEditDraft | null = null
  let invalid = ''
  if (stored.input) {
    try { draft = restoreVisualEdit(stored.input, document.id, version) }
    catch (reason) { invalid = reason instanceof Error ? reason.message : 'Draft recovery unavailable.' }
  }
  const locked = busy || !!recovery.pending || recovery.needsDiscard
  function edit(edits: VisualEdits) { if (draft) { setUndo(old => [...old.slice(-19), draft!.edits]); stored.setInput(JSON.stringify({ ...draft, edits })); setSaved('') } }
  async function begin() {
    if (active.current || readOnly) return
    const controller = new AbortController(); active.current = controller; setBusy(true); setError('')
    try {
      const current = await boundedRead<Document>(`/api/authored-visuals/${document.id}`, controller.signal, 'Current diagram')
      const latest = await boundedRead<Schemas['VisualVersionSummary'][]>(`/api/authored-visuals/${document.id}/versions?limit=1`, controller.signal, 'Latest version')
      if (!mounted.current || controller.signal.aborted) return
      if (current.archived || latest[0]?.id !== version.id || version.spec?.schema_version !== 'visual.answer.v1') throw new Error('Open the latest active version before starting an edit.')
      stored.setInput(JSON.stringify({ schema: 'visual-edit.v1', documentId: document.id, revision: current.revision, versionId: version.id, contentHash: version.content_sha256, edits: editableFields(version.spec) } satisfies VisualEditDraft))
    } catch (reason) { if (mounted.current) setError(reason instanceof Error ? reason.message : 'Could not start editing.') }
    finally { if (mounted.current) { active.current = null; setBusy(false) } }
  }
  async function save(previous?: PendingTutorRequest<ReturnType<typeof visualSaveBody>>) {
    if (active.current || (!previous && (readOnly || locked || !draft))) return
    const controller = new AbortController(); active.current = controller; setBusy(true); setError(''); setSaved('')
    try {
      const intent = previous ?? recovery.prepare(visualSaveBody(draft!, version), { display: `Edit version ${version.version}: ${draft!.edits.title}`, submitted: '', snapshot: '', mode: 'explicit' })
      const result = await boundedRead<Schemas['VisualReceipt']>('/api/authored-visuals/commands', controller.signal, 'Save diagram version', { method: 'POST', headers: { 'Idempotency-Key': intent.key }, body: JSON.stringify(intent.body) })
      if (!mounted.current || controller.signal.aborted) return
      recovery.accept(intent.key)
      setSaved(`New version saved (${result.version_id}). Your draft remains available; open the latest version before making another save.`)
      await cache.invalidateQueries({ queryKey: ['visual-documents', learnerId] })
      await cache.invalidateQueries({ queryKey: ['visual-versions', learnerId, document.id] })
    } catch (reason) { if (mounted.current) setError(reason instanceof Error ? reason.message : 'Save not confirmed. Your draft is kept.') }
    finally { if (mounted.current) { active.current = null; setBusy(false) } }
  }
  async function compare() {
    if (active.current) return
    const controller = new AbortController(); active.current = controller; setBusy(true); setError('')
    try {
      const rows = await boundedRead<Schemas['VisualVersionSummary'][]>(`/api/authored-visuals/${document.id}/versions?limit=1`, controller.signal, 'Latest version')
      if (!rows[0]) throw new Error('No saved version is available.')
      const result = await boundedRead<Schemas['VisualVersionDetail']>(`/api/authored-visuals/${document.id}/versions/${rows[0].id}`, controller.signal, 'Compare latest version')
      if (mounted.current && !controller.signal.aborted) setComparison(result)
    } catch (reason) { if (mounted.current) setError(reason instanceof Error ? reason.message : 'Comparison unavailable.') }
    finally { if (mounted.current) { active.current = null; setBusy(false) } }
  }
  const edits = draft?.edits
  return <Disclosure label={`Edit diagram · based on version ${version.version}`}>
    <div className="space-y-3">
      <p>Edits save a new version. Sources and earlier reviews remain attached to their original history; your changes are not fact-checked.</p>
      {readOnly && <p>New saves require the latest active version. Your existing draft and retry stay available here.</p>}
      {!stored.input && <Button disabled={readOnly || locked} onClick={() => void begin()}>Start editing this version</Button>}
      {stored.error && <p role="alert">{stored.error}</p>}{invalid && <p role="alert">{invalid}</p>}
      {edits && <fieldset disabled={busy} className="space-y-3">
        <Button disabled={!undo.length} onClick={() => { const previous = undo.at(-1); if (draft && previous) { stored.setInput(JSON.stringify({ ...draft, edits: previous })); setUndo(old => old.slice(0, -1)); setSaved('') } }}>Undo last edit</Button>
        <label className="block">Diagram title<input className={field} maxLength={240} value={edits.title} onChange={e => edit({ ...edits, title: e.target.value })} /></label>
        <label className="block">Complete text explanation<textarea className={field} rows={4} maxLength={8000} value={edits.text_equivalent} onChange={e => edit({ ...edits, text_equivalent: e.target.value })} /></label>
        <label><input type="checkbox" checked={edits.directed} onChange={e => edit({ ...edits, directed: e.target.checked })} />Relationships have a direction</label>
        {edits.nodes.map((node, index) => <fieldset key={node.id} className="rounded border border-line p-3 space-y-2"><legend>Concept {index + 1}</legend>
          <label>Concept label<input className={field} maxLength={240} value={node.label} onChange={e => edit({ ...edits, nodes: edits.nodes.map(n => n.id === node.id ? { ...n, label: e.target.value } : n) })} /></label>
          <label>Concept explanation<textarea className={field} maxLength={1200} value={node.explanation} onChange={e => edit({ ...edits, nodes: edits.nodes.map(n => n.id === node.id ? { ...n, explanation: e.target.value } : n) })} /></label>
          <Button onClick={() => edit({ ...edits, nodes: edits.nodes.filter(n => n.id !== node.id) })}>Remove concept {index + 1}</Button>
        </fieldset>)}
        <Button disabled={edits.nodes.length >= 64} onClick={() => edit({ ...edits, nodes: [...edits.nodes, { id: `node_${crypto.randomUUID()}`, label: '', explanation: '' }] })}>Add concept</Button>
        {edits.edges.map((edge, index) => <fieldset key={edge.id} className="rounded border border-line p-3 space-y-2"><legend>Relationship {index + 1}</legend>
          {(['source', 'target'] as const).map(endpoint => <label key={endpoint} className="block">{endpoint === 'source' ? 'From concept' : 'To concept'}<select className={field} value={edge[endpoint]} onChange={e => edit({ ...edits, edges: edits.edges.map(v => v.id === edge.id ? { ...v, [endpoint]: e.target.value } : v) })}>{!edits.nodes.some(n => n.id === edge[endpoint]) && <option value={edge[endpoint]}>Choose a concept</option>}{edits.nodes.map(n => <option key={n.id} value={n.id}>{n.label || 'Untitled concept'}</option>)}</select></label>)}
          <label>Relationship meaning<input className={field} maxLength={240} value={edge.label} onChange={e => edit({ ...edits, edges: edits.edges.map(v => v.id === edge.id ? { ...v, label: e.target.value } : v) })} /></label>
          <Button onClick={() => edit({ ...edits, edges: edits.edges.filter(v => v.id !== edge.id) })}>Remove relationship {index + 1}</Button>
        </fieldset>)}
        <Button disabled={edits.edges.length >= 128} onClick={() => edit({ ...edits, edges: [...edits.edges, { id: `edge_${crypto.randomUUID()}`, source: edits.nodes[0]?.id ?? '', target: edits.nodes[1]?.id ?? '', label: '' }] })}>Add relationship</Button>
        {!validVisualEdits(edits) && <p role="status">Complete all text fields and choose existing concepts for each relationship before previewing or saving.</p>}
        <div className="flex flex-wrap gap-2"><Button disabled={!validVisualEdits(edits)} onClick={() => setPreview(!preview)}>{preview ? 'Hide draft preview' : 'Preview draft'}</Button><Button disabled={readOnly || locked || !validVisualEdits(edits) || !!saved} onClick={() => void save()}>Save as new version</Button></div>
        {preview && validVisualEdits(edits) && <section aria-label="Unsaved diagram preview"><p>Unsaved preview · not fact-checked</p><VisualFallback><Suspense fallback={<p>Loading preview…</p>}><RelationshipGraph graph={{ title: edits.title, textEquivalent: edits.text_equivalent, directed: edits.directed, nodes: edits.nodes, edges: edits.edges }} /></Suspense></VisualFallback></section>}
      </fieldset>}
      <RequestRecoveryControls saveOnly savedAction="save another version" recovery={recovery} busy={busy} originalContext="diagram, original revision and submitted edits" retry={() => { if (recovery.pending) void save(recovery.pending) }} />
      {busy && <Button onClick={() => active.current?.abort()}>Stop waiting for editor</Button>}
      {error && <p role="alert">{error}</p>}{saved && <p role="status">{saved}</p>}
      {draft && <><Button disabled={busy} onClick={() => void compare()}>Compare latest saved version</Button>{comparison?.spec && <section aria-label="Latest version comparison"><h4>Latest saved version {comparison.version}: {comparison.spec.title}</h4><p>{comparison.spec.text_equivalent}</p><ul>{comparison.spec.nodes.map(n => <li key={n.id}>{n.label}: {n.explanation}</li>)}</ul><ul>{comparison.spec.edges.map(e => <li key={e.id}>{e.source} → {e.target}: {e.label}</li>)}</ul><p>Your draft above is unchanged. Open the latest version to start a separate edit; copy across only changes you want to keep. Nothing is merged automatically.</p></section>}</>}
      {!!stored.input && <Disclosure label="Keep a copy or discard this draft"><p>Copy this recovery text before discarding. It may contain source-derived material; keep it private.</p><textarea aria-label="Diagram draft recovery copy" className={field} readOnly value={stored.input} rows={3} /><Button disabled={locked} onClick={() => { stored.setInput(''); setSaved(''); setPreview(false); setComparison(null); setUndo([]) }}>Discard this draft</Button></Disclosure>}
    </div>
  </Disclosure>
}
