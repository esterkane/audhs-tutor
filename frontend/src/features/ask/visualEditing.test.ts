import { describe, expect, it } from 'vitest'
import type { Schemas } from '../../lib/api'
import { applyVisualEdits, editableFields, restoreVisualEdit, validVisualEdits, visualSaveBody, type VisualEditDraft } from './visualEditing'
const spec: Schemas['AnswerRelationshipVisual'] = {
  schema_version: 'visual.answer.v1', kind: 'relationship', title: 'Fit then apply', text_equivalent: 'Fit on training data; apply to held-out data.', directed: true,
  binding: { schema_version: 'answer-visual-binding.v1', answer_id: 'answer', question_sha256: 'a'.repeat(64), answer_sha256: 'b'.repeat(64), lineage_sha256: 'c'.repeat(64), learning_purpose: null },
  source_chunk_ids: ['source'], nodes: [{ id: 'fit', label: 'Fit', explanation: 'Training only', source_chunk_ids: ['source'] }, { id: 'apply', label: 'Apply', explanation: 'Use the fitted parameters', source_chunk_ids: [] }],
  edges: [{ id: 'next', source: 'fit', target: 'apply', label: 'then', source_chunk_ids: ['source'] }],
}
const version: Schemas['VisualVersionDetail'] = { id: 'v1', version: 1, content_sha256: 'd'.repeat(64), snapshot_sha256: 'e'.repeat(64), target_kind: 'answer', target_id: 'answer', created_at: '2026-10-13', spec, grounding_now: 'sources_recorded', review_meaning: 'historical_presentation_review_only' }
const draft = (): VisualEditDraft => ({ schema: 'visual-edit.v1', documentId: 'doc', versionId: 'v1', contentHash: version.content_sha256, revision: 3, edits: editableFields(spec) })

describe('immutable visual editing contract', () => {
  it('keeps binding and source restrictions while editing and adding parts', () => {
    const edits = editableFields(spec)
    edits.nodes[0].explanation = 'Estimate parameters using training examples only.'
    edits.nodes.push({ id: 'check', label: 'Check', explanation: 'Evaluate on held-out examples.' })
    edits.edges[0].target = 'check'
    const result = applyVisualEdits(spec, edits)
    expect(result.binding).toEqual(spec.binding)
    expect(result.source_chunk_ids).toEqual(['source'])
    expect(result.nodes[0].source_chunk_ids).toEqual(['source'])
    expect(result.edges[0].source_chunk_ids).toEqual(['source'])
    expect(result.nodes[2].source_chunk_ids).toEqual([])
    result.binding.answer_id = 'mutated-copy'
    expect(spec.binding.answer_id).toBe('answer')
    expect(spec.nodes[0].explanation).toBe('Training only')
  })
  it('retains the original revision across reload, never rebasing a draft silently', () => {
    const body = visualSaveBody(restoreVisualEdit(JSON.stringify(draft()), 'doc', version), version)
    expect(body.expected_revision).toBe(3)
    expect(body.spec).toEqual(spec)
    expect(() => restoreVisualEdit(JSON.stringify(draft()), 'another-document', version)).toThrow()
    expect(() => restoreVisualEdit(JSON.stringify(draft()), 'doc', { ...version, id: 'v2' })).toThrow()
    expect(() => restoreVisualEdit(JSON.stringify(draft()), 'doc', { ...version, content_sha256: 'f'.repeat(64) })).toThrow()
  })
  it('rejects injected provenance, duplicate identities, dangling endpoints and oversized content', () => {
    expect(validVisualEdits({ ...editableFields(spec), binding: spec.binding })).toBe(false)
    const edits = editableFields(spec)
    edits.nodes.push(edits.nodes[0])
    expect(validVisualEdits(edits)).toBe(false)
    edits.nodes.pop(); edits.edges[0].target = 'missing'
    expect(validVisualEdits(edits)).toBe(false)
    edits.edges[0].target = 'fit'; edits.title = 'x'.repeat(241)
    expect(validVisualEdits(edits)).toBe(false)
    expect(() => restoreVisualEdit('{broken', 'doc', version)).toThrow()
  })
  it('recovers unfinished text and topology without permitting an invalid save', () => {
    const partial = draft()
    partial.edits.title = ''
    partial.edits.nodes = []
    expect(restoreVisualEdit(JSON.stringify(partial), 'doc', version)).toEqual(partial)
    expect(() => visualSaveBody(partial, version)).toThrow('Check diagram fields')
  })
  it('bounds actual UTF-8 command bytes, not only individual fields', () => {
    const large = draft()
    large.edits.nodes = Array.from({ length: 64 }, (_, i) => ({ id: `node${i}`, label: 'Node', explanation: '界'.repeat(1200) }))
    large.edits.edges = []
    expect(validVisualEdits(large.edits)).toBe(true)
    expect(() => visualSaveBody(large, version)).toThrow('save size limit')
  })
  it('allows meaningful cycles and parallel edges, without rendering executable markup', () => {
    const edits = editableFields(spec)
    edits.nodes[0].label = '<script>alert(1)</script>'
    edits.edges.push({ id: 'back', source: 'apply', target: 'fit', label: 'feedback' })
    expect(validVisualEdits(edits)).toBe(true)
    expect(applyVisualEdits(spec, edits).nodes[0].label).toBe('<script>alert(1)</script>')
  })
})
