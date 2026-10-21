import { Outlet } from "react-router-dom"

import { AppSidebar } from "@/components/layout/AppSidebar"
import { Topbar } from "@/components/layout/Topbar"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"

export function AppShell() {
  return (
    <SidebarProvider>
      <div className="flex min-h-svh w-full">
        <AppSidebar />
        <SidebarInset>
          <Topbar />
          <div className="mx-auto w-full max-w-7xl p-4 sm:p-6 lg:p-8">
            <Outlet />
          </div>
        </SidebarInset>
      </div>
    </SidebarProvider>
  )
}
