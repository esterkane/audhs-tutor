import type { ComponentPropsWithRef, ComponentPropsWithoutRef } from 'react'
import { ChevronRight } from 'lucide-react'
import { cn } from '../../lib/utils'

type DisclosureProps = ComponentPropsWithoutRef<'details'> & { label: string }

/** Native toggle/focus semantics; children stay mounted when collapsed. */
export function Disclosure({ label, children, className, ...props }: DisclosureProps) {
  return (
    <details
      className={cn('rounded-panel border border-line bg-card [&[open]>summary>svg]:rotate-90', className)}
      {...props}
    >
      <DisclosureSummary>{label}</DisclosureSummary>
      <div className="px-3 pb-3">{children}</div>
    </details>
  )
}

/** Shared row for disclosures whose body or focus owner needs custom composition. */
export function DisclosureSummary({ children, className, ...props }: ComponentPropsWithRef<'summary'>) {
  return <summary className={cn('flex min-h-control-target cursor-pointer list-none items-center gap-2 px-3 py-2 text-sm font-medium [&::-webkit-details-marker]:hidden', className)} {...props}>
    <ChevronRight size={16} strokeWidth={1.75} className="shrink-0" aria-hidden="true" />
    <span className="min-w-0 break-words">{children}</span>
  </summary>
}
