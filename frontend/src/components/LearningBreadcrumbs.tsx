/** Read-only orientation from the displayed content, never browsing preferences. */
export function LearningBreadcrumbs({ items, label = 'Learning path' }: { items: string[]; label?: string }) {
  return <nav aria-label={label} className="text-sm text-muted min-w-0">
    <ol className="flex flex-wrap gap-x-2 gap-y-1 min-w-0">
      {items.map((item, i) => <li key={i} className="min-w-0 break-words [overflow-wrap:anywhere]" aria-current={i === items.length - 1 ? 'step' : undefined}>
        {i > 0 && <span aria-hidden="true" className="mr-2">›</span>}{item}
      </li>)}
    </ol>
  </nav>
}
