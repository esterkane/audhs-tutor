export type Section = {
  id: string
  title: string
  explanation: string
  task: string
  question: string
  hint: string
  criteria: string
  source: string
  practice?: { notebook: string; dataset?: string }
  example?: string
  challenges?: { id: string; question: string; hint: string; criteria: string }[]
}
export type Course = {
  id: string
  title: string
  project: string
  status: string
  explanations?: Record<string, string>
  notebook?: string
  sections: Section[]
}
export type Program = { title: string; courses: Course[] }
export function parseProgram(raw: unknown): Program {
  const p = raw as Program
  if (!p || typeof p.title !== 'string' || !Array.isArray(p.courses))
    throw new Error('Invalid local programme manifest.')
  const ids = new Set<string>()
  for (const c of p.courses) {
    if (
      !c ||
      ['id', 'title', 'project', 'status'].some((k) => typeof c[k as keyof Course] !== 'string') ||
      !Array.isArray(c.sections) ||
      ids.has(c.id)
    )
      throw new Error('Invalid course entry.')
    if (
      c.notebook !== undefined &&
      (typeof c.notebook !== 'string' || !/^\/local-learning\/[a-zA-Z0-9_-]+\.ipynb$/.test(c.notebook))
    )
      throw new Error('Saved notebook must be a local learning file.')
    if (
      c.explanations !== undefined &&
      (!c.explanations ||
        typeof c.explanations !== 'object' ||
        Array.isArray(c.explanations) ||
        Object.values(c.explanations).some((v) => typeof v !== 'string'))
    )
      throw new Error('Invalid notebook explanations.')
    ids.add(c.id)
    const sectionIds = new Set<string>()
    for (const s of c.sections) {
      if (
        !s ||
        ['id', 'title', 'explanation', 'task', 'question', 'hint', 'criteria', 'source'].some(
          (k) => typeof s[k as keyof Section] !== 'string',
        ) ||
        sectionIds.has(s.id)
      )
        throw new Error('Invalid section entry.')
      if (
        s.practice !== undefined &&
        (!s.practice ||
          typeof s.practice.notebook !== 'string' ||
          !/^\/local-learning\/[a-zA-Z0-9_-]+\.ipynb$/.test(s.practice.notebook) ||
          (s.practice.dataset !== undefined &&
            (typeof s.practice.dataset !== 'string' ||
              !/^\/local-learning\/[a-zA-Z0-9_-]+\.csv$/.test(s.practice.dataset))))
      )
        throw new Error('Invalid local practice files.')
      if (s.example !== undefined && typeof s.example !== 'string') throw new Error('Invalid worked example.')
      if (s.challenges !== undefined) {
        if (!Array.isArray(s.challenges) || s.challenges.length > 8) throw new Error('Invalid challenges.')
        const challengeIds = new Set<string>()
        for (const q of s.challenges) {
          if (
            !q ||
            ['id', 'question', 'hint', 'criteria'].some((k) => typeof q[k as keyof typeof q] !== 'string') ||
            !q.id.trim() ||
            q.id === 'main' ||
            challengeIds.has(q.id)
          )
            throw new Error('Invalid challenge entry.')
          challengeIds.add(q.id)
        }
      }
      sectionIds.add(s.id)
    }
  }
  return p
}
export type NotebookCell = { cell_type: 'code' | 'markdown' | 'raw'; source: string }
export function parseNotebook(raw: unknown): NotebookCell[] {
  const notebook = raw as { cells?: { cell_type?: string; source?: unknown }[]; nbformat?: number }
  if (notebook?.nbformat !== 4 || !Array.isArray(notebook.cells) || notebook.cells.length > 3000)
    throw new Error('Choose a version 4 Jupyter notebook with at most 3,000 cells.')
  return notebook.cells
    .filter((c) => c.cell_type === 'code' || c.cell_type === 'markdown' || c.cell_type === 'raw')
    .map((c) => {
      const source =
        typeof c.source === 'string'
          ? c.source
          : Array.isArray(c.source) && c.source.every((x) => typeof x === 'string')
            ? c.source.join('')
            : null
      if (source === null) throw new Error('Notebook cell has invalid source text.')
      return { cell_type: c.cell_type as NotebookCell['cell_type'], source }
    })
}
