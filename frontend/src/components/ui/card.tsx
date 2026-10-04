import * as React from 'react'
import { cn } from '../../lib/utils'

type CardProps = React.HTMLAttributes<HTMLDivElement> & { lift?: boolean }

export function Card({ className, lift = false, ...props }: CardProps) {
  return <div className={cn('rounded-panel border border-line bg-card p-4', lift && 'shadow-panel', className)} {...props} />
}

type CardTitleProps = React.HTMLAttributes<HTMLHeadingElement> & {
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6'
}

export function CardTitle({ as: Heading = 'h2', className, ...props }: CardTitleProps) {
  return <Heading className={cn('font-semibold mb-3', Heading === 'h1' ? 'text-page-title' : 'text-panel-heading', className)} {...props} />
}
