import type { ComponentPropsWithoutRef } from 'react'
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
      <summary className="flex min-h-11 cursor-pointer list-none items-center gap-2 px-3 py-2 text-sm font-medium [&::-webkit-details-marker]:hidden">
        <ChevronRight size={16} strokeWidth={1.75} className="shrink-0" aria-hidden="true" />
        <span className="min-w-0 break-words">{label}</span>
      </summary>
      <div className="px-3 pb-3">{children}</div>
    </details>
  )
}
