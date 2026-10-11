import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import * as React from 'react'
import { cn } from '../../lib/utils'

const buttonVariants = cva(
  'relative isolate inline-flex min-w-control-target items-center justify-center gap-2 rounded-md text-sm font-medium before:pointer-events-none before:absolute before:inset-x-0 before:inset-y-[var(--button-inset)] before:-z-10 before:rounded-md disabled:before:bg-sunken disabled:text-faint disabled:opacity-100 disabled:pointer-events-none select-none',
  {
    variants: {
      variant: {
        primary: 'before:bg-accent text-accent-fg hover:before:bg-accent-hover',
        secondary: 'before:bg-card before:border before:border-control hover:before:bg-bg',
        ghost: 'text-accent hover:before:bg-line/50',
        outline: 'before:border before:border-control hover:before:bg-card',
      },
      size: {
        sm: 'button-compact min-h-control-target px-3 py-2.5',
        md: 'button-standard min-h-control-target px-4 py-2.5',
        lg: '[--button-inset:0px] min-h-12 px-5 py-2 text-base',
      },
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
