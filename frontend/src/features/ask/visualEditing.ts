import type { Schemas } from '../../lib/api'

type Spec = Schemas['AnswerRelationshipVisual']
export type VisualEdits = {
  title: string; text_equivalent: string; directed: boolean;
  nodes: { id: string; label: string; explanation: string }[];
  edges: { id: string; source: string; target: string; label: string }[];
}
export type VisualEditDraft = {
  schema: 'visual-edit.v1'; documentId: string; revision: number;
  versionId: string; contentHash: string; edits: VisualEdits;
}
const id = /^[A-Za-z][A-Za-z0-9_-]{0,63}$/
const hash = /^[a-f0-9]{64}$/
const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value)
const text = (value: unknown, max: number): value is string => typeof value === 'string' && value.length > 0 && value.length <= max
const exact = (value: Record<string, unknown>, keys: string[]) => Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key))

/** Only editable fields enter the draft; source and binding fields are never user patches. */
export function editableFields(spec: Spec): VisualEdits {
  return {
    title: spec.title, text_equivalent: spec.text_equivalent, directed: spec.directed,
    nodes: spec.nodes.map(({ id, label, explanation }) => ({ id, label, explanation })),
    edges: spec.edges.map(({ id, source, target, label }) => ({ id, source, target, label })),
  }
}

export function validVisualEdits(value: unknown, forSave = true): value is VisualEdits {
  const field = (value: unknown, max: number) => typeof value === 'string' && value.length <= max && (!forSave || text(value, max))
  if (!object(value) || !exact(value, ['title', 'text_equivalent', 'directed', 'nodes', 'edges'])
    || !field(value.title, 240) || !field(value.text_equivalent, 8000) || typeof value.directed !== 'boolean'
    || !Array.isArray(value.nodes) || (forSave && value.nodes.length < 1) || value.nodes.length > 64
    || !Array.isArray(value.edges) || value.edges.length > 128) return false
  const nodeIds = new Set<string>()
  for (const node of value.nodes) {
    if (!object(node) || !exact(node, ['id', 'label', 'explanation']) || typeof node.id !== 'string' || !id.test(node.id)
      || nodeIds.has(node.id) || !field(node.label, 240) || !field(node.explanation, 1200)) return false
    nodeIds.add(node.id)
  }
  const edgeIds = new Set<string>()
  for (const edge of value.edges) {
    if (!object(edge) || !exact(edge, ['id', 'source', 'target', 'label']) || typeof edge.id !== 'string' || !id.test(edge.id)
      || edgeIds.has(edge.id) || !field(edge.label, 240) || typeof edge.source !== 'string' || (forSave && !nodeIds.has(edge.source))
      || typeof edge.target !== 'string' || (forSave && !nodeIds.has(edge.target))) return false
    edgeIds.add(edge.id)
  }
  return true
}

/** Reconstruct from the immutable server version, retaining its full origin restrictions. */
export function applyVisualEdits(base: Spec, edits: VisualEdits): Spec {
  if (!validVisualEdits(edits)) throw new Error('Check diagram fields and relationship endpoints before saving.')
  const nodes = new Map(base.nodes.map(node => [node.id, node]))
  const edges = new Map(base.edges.map(edge => [edge.id, edge]))
  return {
    ...base, ...structuredClone(edits), binding: structuredClone(base.binding),
    source_chunk_ids: [...(base.source_chunk_ids ?? [])],
    nodes: edits.nodes.map(node => ({ ...node, source_chunk_ids: [...(nodes.get(node.id)?.source_chunk_ids ?? [])] })),
    edges: edits.edges.map(edge => ({ ...edge, source_chunk_ids: [...(edges.get(edge.id)?.source_chunk_ids ?? [])] })),
  }
}

export function restoreVisualEdit(raw: string, documentId: string, version: Schemas['VisualVersionDetail']): VisualEditDraft {
  if (raw.length > 200000) throw new Error('Saved diagram draft exceeds the recovery limit.')
  const value: unknown = JSON.parse(raw)
  if (!object(value) || !exact(value, ['schema', 'documentId', 'revision', 'versionId', 'contentHash', 'edits'])
    || value.schema !== 'visual-edit.v1' || value.documentId !== documentId || value.versionId !== version.id
    || typeof value.contentHash !== 'string' || !hash.test(value.contentHash) || value.contentHash !== version.content_sha256
    || !Number.isSafeInteger(value.revision) || (value.revision as number) < 1 || !validVisualEdits(value.edits, false)) {
    throw new Error('This draft does not match the saved diagram version. Keep a copy before discarding it.')
  }
  return value as VisualEditDraft
}

export function visualSaveBody(draft: VisualEditDraft, version: Schemas['VisualVersionDetail']) {
  // Check even in-memory drafts, not just browser-restored strings.
  restoreVisualEdit(JSON.stringify(draft), draft.documentId, version)
  if (version.spec?.schema_version !== 'visual.answer.v1') throw new Error('This diagram version cannot be edited.')
  const body = { action: 'save' as const, document_id: draft.documentId, expected_revision: draft.revision,
    spec: applyVisualEdits(version.spec, draft.edits) }
  if (new TextEncoder().encode(JSON.stringify(body)).length > 131072) throw new Error('Diagram exceeds the save size limit. Shorten its text before saving.')
  return body
}
