import * as React from 'react'
import { cn } from '../../lib/utils'

export function Textarea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn('w-full rounded-md border border-line bg-card p-3 text-base min-h-24', className)}
      {...props}
    />
  )
}
