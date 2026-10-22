import { cn } from "@/lib/utils"

export function Alert({ className, ...props }) {
  return (
    <div
      role="alert"
      className={cn(
        "relative w-full rounded-lg border px-4 py-3 text-sm [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-3.5 [&>svg]:size-4 [&>svg~*]:pl-7",
        className,
      )}
      {...props}
    />
  )
}

export function AlertDescription({ className, ...props }) {
  return <div className={cn("leading-relaxed", className)} {...props} />
}
