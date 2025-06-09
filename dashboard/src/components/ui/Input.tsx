import { cn } from './cn'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Input: React.FC<InputProps> = ({ className, ...props }) => (
  <input
    className={cn('border border-gray-300 p-2 rounded w-full', className)}
    {...props}
  />
)
