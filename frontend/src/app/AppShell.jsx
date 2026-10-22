import { useEffect, useRef } from "react"
import { Outlet, useLocation } from "react-router-dom"

import { AppSidebar } from "@/components/layout/AppSidebar"
import { Topbar } from "@/components/layout/Topbar"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"

export function AppShell() {
  const { pathname } = useLocation()
  const contentRef = useRef(null)

  // Only the content area scrolls, and it stays mounted across pages: start each page at the top.
  useEffect(() => {
    contentRef.current?.scrollTo({ top: 0 })
  }, [pathname])

  return (
    <SidebarProvider>
      <div className="flex h-svh w-full overflow-hidden">
        <AppSidebar />
        <SidebarInset className="flex min-h-0 flex-col">
          <Topbar />
          <div ref={contentRef} className="min-h-0 flex-1 overflow-y-auto">
            <div className="mx-auto w-full max-w-7xl p-4 sm:p-6 lg:p-8">
              <Outlet />
            </div>
          </div>
        </SidebarInset>
      </div>
    </SidebarProvider>
  )
}
