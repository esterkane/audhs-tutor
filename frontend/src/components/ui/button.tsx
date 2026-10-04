import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import * as React from 'react'
import { cn } from '../../lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 rounded-md text-sm font-medium disabled:bg-sunken disabled:text-faint disabled:opacity-100 disabled:pointer-events-none select-none',
  {
    variants: {
      variant: {
        primary: 'bg-accent text-accent-fg hover:bg-accent-hover',
        secondary: 'bg-card border border-control hover:bg-bg',
        ghost: 'text-accent hover:bg-line/50',
        outline: 'border border-control bg-transparent hover:bg-card',
      },
      size: { sm: 'min-h-8 px-3 py-1', md: 'min-h-10 px-4 py-2', lg: 'min-h-12 px-5 py-2 text-base' },
    },
    defaultVariants: { variant: 'secondary', size: 'md' },
  },
)

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants> & {
    asChild?: boolean
    pressed?: boolean
  }

export function Button({ className, variant, size, asChild, pressed, type, ...props }: ButtonProps) {
  const Comp = asChild ? Slot : 'button'
  return (
    <Comp
      type={asChild ? undefined : (type ?? 'button')}
      aria-pressed={pressed}
      className={cn(buttonVariants({ variant, size }), pressed && 'ring-2 ring-accent', className)}
      {...props}
    />
  )
}
