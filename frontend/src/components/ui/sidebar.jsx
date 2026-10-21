import { Slot } from "@radix-ui/react-slot"
import { PanelLeft } from "lucide-react"
import { createContext, forwardRef, useContext, useMemo, useState } from "react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const SidebarContext = createContext(null)

export function SidebarProvider({ children }) {
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)
  const value = useMemo(
    () => ({ collapsed, setCollapsed, mobileOpen, setMobileOpen }),
    [collapsed, mobileOpen],
  )
  return (
    <SidebarContext.Provider value={value}>{children}</SidebarContext.Provider>
  )
}

export function useSidebar() {
  const value = useContext(SidebarContext)
  if (!value) throw new Error("useSidebar must be used inside SidebarProvider")
  return value
}

export function Sidebar({ className, children }) {
  const { collapsed } = useSidebar()
  return (
    <aside
      data-collapsed={collapsed}
      className={cn(
        "hidden h-svh shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-200 md:flex",
        collapsed ? "w-16" : "w-72",
        className,
      )}
    >
      {children}
    </aside>
  )
}

export function SidebarInset({ className, ...props }) {
  return (
    <main
      className={cn("min-w-0 flex-1 bg-background", className)}
      {...props}
    />
  )
}

export function SidebarHeader({ className, ...props }) {
  return (
    <div
      className={cn("border-b border-sidebar-border p-3", className)}
      {...props}
    />
  )
}

export function SidebarContent({ className, ...props }) {
  return (
    <div
      className={cn(
        "flex min-h-0 flex-1 flex-col overflow-y-auto p-2",
        className,
      )}
      {...props}
    />
  )
}

export function SidebarFooter({ className, ...props }) {
  return (
    <div
      className={cn("border-t border-sidebar-border p-3", className)}
      {...props}
    />
  )
}

export function SidebarMenu({ className, ...props }) {
  return (
    <ul className={cn("flex w-full flex-col gap-1", className)} {...props} />
  )
}

export function SidebarMenuItem({ className, ...props }) {
  return <li className={cn("relative", className)} {...props} />
}

export const SidebarMenuButton = forwardRef(
  ({ asChild = false, className, isActive = false, ...props }, ref) => {
    const Component = asChild ? Slot : "button"
    return (
      <Component
        ref={ref}
        data-active={isActive}
        className={cn(
          "flex h-9 w-full min-w-0 items-center gap-3 overflow-hidden rounded-md px-3 text-left text-sm font-medium text-sidebar-foreground outline-none transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground focus-visible:ring-2 focus-visible:ring-sidebar-ring data-[active=true]:bg-sidebar-accent data-[active=true]:text-sidebar-accent-foreground [&>svg]:size-4 [&>svg]:shrink-0",
          className,
        )}
        {...props}
      />
    )
  },
)
SidebarMenuButton.displayName = "SidebarMenuButton"

export function SidebarTrigger({ className, mobile = false }) {
  const { collapsed, setCollapsed, setMobileOpen } = useSidebar()
  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className={className}
      onClick={() => (mobile ? setMobileOpen(true) : setCollapsed(!collapsed))}
      aria-label={mobile ? "Open navigation" : "Toggle navigation"}
    >
      <PanelLeft />
    </Button>
  )
}
