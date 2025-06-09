import { cn } from './cn'

export const Card: React.FC<React.HTMLAttributes<HTMLDivElement>> = ({ className, ...props }) => (
  <div className={cn('p-4 border rounded bg-white shadow', className)} {...props} />
)
