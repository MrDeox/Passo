import { cn } from './cn'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {}

export const Button: React.FC<ButtonProps> = ({ className, ...props }) => (
  <button
    className={cn('px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700', className)}
    {...props}
  />
)
