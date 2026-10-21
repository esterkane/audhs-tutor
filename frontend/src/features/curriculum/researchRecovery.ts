import type { Schemas } from '../../lib/api'
type Research = Schemas['KnowledgeResearch']

export function sameKnowledgeMaterial(left: Schemas['KnowledgeMaterialInput'], right: Schemas['KnowledgeMaterialInput']): boolean {
  function canonical(value: unknown): string {
    if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`
    if (value && typeof value === 'object') return `{${Object.entries(value).sort(([a], [b]) => a.localeCompare(b)).map(([key, item]) => `${JSON.stringify(key)}:${canonical(item)}`).join(',')}}`
    return JSON.stringify(value) ?? 'null'
  }
  const leftContent = Object.fromEntries(Object.entries(left).filter(([key]) => key !== 'workflow_step'))
  const rightContent = Object.fromEntries(Object.entries(right).filter(([key]) => key !== 'workflow_step'))
  return canonical(leftContent) === canonical(rightContent)
}

export function validResearch(value: unknown): value is Research {
  if (!value || typeof value !== 'object') return false
  const r = value as Research
  return typeof r.passage === 'string' && r.passage.length > 0 && r.passage.length <= 6000
    && typeof r.topic === 'string' && r.topic.length > 0 && r.topic.length <= 300
    && Number.isInteger(r.current) && (r.current ?? -1) >= 0
    && Array.isArray(r.questions) && r.questions.length > 0 && r.questions.length <= 12
    && r.current! < r.questions.length
    && r.questions.every(q => typeof q.id === 'string' && typeof q.prompt === 'string'
      && (q.source_quote == null || (typeof q.source_quote === 'string' && r.passage.includes(q.source_quote)))
      && (q.memory_ids === undefined || (Array.isArray(q.memory_ids) && q.memory_ids.length <= 3 && q.memory_ids.every(id => typeof id === 'string')))
      && (q.tutor_request === undefined || typeof q.tutor_request === 'string')
      && (q.tutor_basis === undefined || typeof q.tutor_basis === 'string')
      && (q.tutor_exchanges === undefined || (Array.isArray(q.tutor_exchanges) && q.tutor_exchanges.length <= 12
        && q.tutor_exchanges.every(x => x && ['discuss', 'draft'].includes(x.action)
          && (x.cache_token == null || typeof x.cache_token === 'string')
          && typeof x.request === 'string' && typeof x.model_call_id === 'string' && x.answer
          && ['discussion', 'needs_check', 'next_question', 'section'].every(k => typeof x.answer[k as keyof typeof x.answer] === 'string')
          && Array.isArray(x.answer.source_quotes) && x.answer.source_quotes.every(quote => typeof quote === 'string'))))
      && q.prompt.length > 0 && q.prompt.length <= 2000
      && ['findings', 'evidence', 'unresolved', 'section'].every(k => typeof q[k as keyof typeof q] === 'string'))
}
