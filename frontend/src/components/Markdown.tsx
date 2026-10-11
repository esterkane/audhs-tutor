import ReactMarkdown from 'react-markdown'
import rehypeKatex from 'rehype-katex'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'

type ContentNode = {
  type: string
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

export function Markdown({ text, headingLevel = 3 }: { text: string; headingLevel?: 2 | 3 | 4 }) {
  return (
    <div className="prose">
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkMath]} rehypePlugins={[rehypeKatex, relativeHeadings(headingLevel)]}>
        {text}
      </ReactMarkdown>
    </div>
  )
}
