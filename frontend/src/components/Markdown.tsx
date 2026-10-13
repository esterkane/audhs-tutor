import ReactMarkdown from 'react-markdown'
import rehypeKatex from 'rehype-katex'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'

type ContentNode = {
  type: string
  value?: string
  tagName?: string
  properties?: Record<string, unknown>
  children?: ContentNode[]
}

/** Presentation only: source text and heading depth differences remain unchanged. */
function relativeHeadings(base: number) {
  return () => (tree: ContentNode) => {
    const headings: ContentNode[] = []
    const visit = (node: ContentNode) => {
      if (node.type === 'element' && /^h[1-6]$/.test(node.tagName ?? '')) headings.push(node)
      node.children?.forEach(visit)
    }
    visit(tree)
    if (!headings.length) return
    const shallowest = Math.min(...headings.map(node => Number(node.tagName![1])))
    for (const node of headings) {
      const offset = Number(node.tagName![1]) - shallowest
      const level = base + offset
      node.tagName = level <= 6 ? `h${level}` : 'div'
      node.properties = { ...node.properties, 'data-content-heading': offset,
        ...(level > 6 ? { role: 'heading', 'aria-level': level } : {}),
      }
    }
  }
}

/** Only recognized citation markers in prose become controls; never code or links. */
function sourceMarkers(keys: readonly string[]) {
  return () => (tree: ContentNode) => {
    const visit = (node: ContentNode) => {
      if (['code', 'pre', 'a', 'button'].includes(node.tagName ?? '')) return
      if (!node.children) return
      node.children = node.children.flatMap(child => {
        if (child.type !== 'text' || !child.value) { visit(child); return [child] }
        const parts: ContentNode[] = []
        let cursor = 0
        for (const match of child.value.matchAll(/\[source:(S[1-9]\d*)\]/g)) {
          if (!keys.includes(match[1])) continue
          parts.push({ type: 'text', value: child.value.slice(cursor, match.index) })
          parts.push({ type: 'element', tagName: 'button', properties: { 'data-source-key': match[1] },
            children: [{ type: 'text', value: match[0] }] })
          cursor = match.index! + match[0].length
        }
        return cursor ? [...parts, { type: 'text', value: child.value.slice(cursor) }] : [child]
      })
    }
    visit(tree)
  }
}

export function Markdown({ text, headingLevel = 3, sourceKeys = [], onSourceReference }: {
  text: string; headingLevel?: 2 | 3 | 4; sourceKeys?: readonly string[]; onSourceReference?: (key: string) => void
}) {
  return (
    <div className="prose">
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex, relativeHeadings(headingLevel), ...(onSourceReference ? [sourceMarkers(sourceKeys)] : [])]}
        components={onSourceReference ? { button: ({ node, children }) => {
          const key = String(node?.properties['data-source-key'] ?? '')
          return <button type="button" className="text-accent underline rounded" aria-label={`Read source ${key}`}
            onClick={() => onSourceReference(key)}>{children}</button>
        } } : undefined}>
        {text}
      </ReactMarkdown>
    </div>
  )
}
