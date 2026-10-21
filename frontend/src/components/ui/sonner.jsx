import { Toaster as Sonner } from "sonner"

export function Toaster(props) {
  return (
    <Sonner
      position="top-right"
      toastOptions={{ className: "font-sans" }}
      {...props}
    />
  )
}
