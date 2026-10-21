import { ChevronDown, LayoutDashboard, Settings } from "lucide-react"
import { useState } from "react"
import { Link, NavLink, useLocation } from "react-router-dom"

import { features } from "@/app/features"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

function Brand({ collapsed = false, onNavigate }) {
  return (
    <Link
      to="/"
      onClick={onNavigate}
      className={cn(
        "flex items-center gap-3 rounded-md px-2 py-1.5",
        collapsed && "justify-center px-0",
      )}
    >
      <span className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-white p-1">
        <img
          src="/logo.jpg"
          alt="SWSS logo"
          className="size-8 object-contain"
        />
      </span>
      {!collapsed && (
        <span className="min-w-0 leading-tight">
          <span className="block truncate font-semibold">SWSS</span>
          <span className="block truncate text-xs text-muted-foreground">
            Social Welfare Support System
          </span>
        </span>
      )}
    </Link>
  )
}

function EmptyFeatureGroup({ feature, compact }) {
  const Icon = feature.nav.icon
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <SidebarMenuButton
          asChild
          className={cn(
            "cursor-default hover:bg-transparent hover:text-sidebar-foreground",
            compact && "justify-center px-0",
          )}
        >
          <div>
            <Icon />
            {!compact && (
              <span className="min-w-0 flex-1 truncate">
                {feature.nav.title}
              </span>
            )}
          </div>
        </SidebarMenuButton>
      </TooltipTrigger>
      {compact && (
        <TooltipContent side="right">{feature.nav.title}</TooltipContent>
      )}
    </Tooltip>
  )
}

function FeatureGroup({ feature, compact, active, onExpand, onNavigate }) {
  const [open, setOpen] = useState(false)
  const Icon = feature.nav.icon
  const expanded = active || open

  return (
    <Collapsible
      open={compact ? false : expanded}
      onOpenChange={(nextOpen) => setOpen(active ? true : nextOpen)}
    >
      <Tooltip>
        <TooltipTrigger asChild>
          <CollapsibleTrigger asChild>
            <SidebarMenuButton
              type="button"
              isActive={active}
              onClick={() => compact && onExpand()}
              className={compact && "justify-center px-0"}
            >
              <Icon />
              {!compact && (
                <>
                  <span className="min-w-0 flex-1 truncate">
                    {feature.nav.title}
                  </span>
                  <ChevronDown
                    className={cn(
                      "transition-transform",
                      expanded && "rotate-180",
                    )}
                  />
                </>
              )}
            </SidebarMenuButton>
          </CollapsibleTrigger>
        </TooltipTrigger>
        {compact && (
          <TooltipContent side="right">{feature.nav.title}</TooltipContent>
        )}
      </Tooltip>
      <CollapsibleContent className="space-y-1 py-1 pl-7">
        {feature.nav.items.map((item) =>
          item.disabled ? (
            <span
              key={item.path}
              className="flex h-8 items-center rounded-md px-3 text-sm text-muted-foreground opacity-50"
              aria-disabled="true"
            >
              {item.title}
            </span>
          ) : (
            <NavLink
              key={item.path}
              to={item.path}
              onClick={onNavigate}
              className={({ isActive }) =>
                cn(
                  "flex h-8 items-center rounded-md px-3 text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                  isActive &&
                    "bg-sidebar-accent font-medium text-sidebar-accent-foreground",
                )
              }
            >
              {item.title}
            </NavLink>
          ),
        )}
      </CollapsibleContent>
    </Collapsible>
  )
}

function Navigation({ mobile = false, onNavigate }) {
  const { pathname } = useLocation()
  const { collapsed, setCollapsed } = useSidebar()
  const compact = collapsed && !mobile

  return (
    <nav aria-label="Main navigation">
      <SidebarMenu>
        <SidebarMenuItem>
          <Tooltip>
            <TooltipTrigger asChild>
              <SidebarMenuButton
                asChild
                isActive={pathname === "/"}
                className={compact && "justify-center px-0"}
              >
                <Link to="/" onClick={onNavigate}>
                  <LayoutDashboard />
                  {!compact && <span>Dashboard</span>}
                </Link>
              </SidebarMenuButton>
            </TooltipTrigger>
            {compact && <TooltipContent side="right">Dashboard</TooltipContent>}
          </Tooltip>
        </SidebarMenuItem>

        {features.map((feature) => {
          const active = feature.nav.items.some(
            (item) => pathname === item.path,
          )
          return (
            <SidebarMenuItem key={feature.key}>
              {feature.nav.items.length === 0 ? (
                <EmptyFeatureGroup feature={feature} compact={compact} />
              ) : (
                <FeatureGroup
                  feature={feature}
                  compact={compact}
                  active={active}
                  onExpand={() => setCollapsed(false)}
                  onNavigate={onNavigate}
                />
              )}
            </SidebarMenuItem>
          )
        })}
      </SidebarMenu>
    </nav>
  )
}

function SettingsLink({ mobile = false, onNavigate }) {
  const { pathname } = useLocation()
  const { collapsed } = useSidebar()
  const compact = collapsed && !mobile

  return (
    <nav aria-label="Settings">
      <SidebarMenu>
        <SidebarMenuItem>
          <Tooltip>
            <TooltipTrigger asChild>
              <SidebarMenuButton
                asChild
                isActive={pathname === "/settings"}
                className={compact && "justify-center px-0"}
              >
                <Link to="/settings" onClick={onNavigate}>
                  <Settings />
                  {!compact && <span>Settings</span>}
                </Link>
              </SidebarMenuButton>
            </TooltipTrigger>
            {compact && <TooltipContent side="right">Settings</TooltipContent>}
          </Tooltip>
        </SidebarMenuItem>
      </SidebarMenu>
    </nav>
  )
}

export function AppSidebar() {
  const { collapsed, mobileOpen, setMobileOpen } = useSidebar()
  return (
    <>
      <Sidebar>
        <SidebarHeader>
          <Brand collapsed={collapsed} />
        </SidebarHeader>
        <SidebarContent>
          <Navigation />
        </SidebarContent>
        <SidebarFooter>
          <SettingsLink />
        </SidebarFooter>
      </Sidebar>

      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetContent side="left" className="w-72 p-0">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <div className="border-b p-3">
            <Brand onNavigate={() => setMobileOpen(false)} />
          </div>
          <div className="flex h-[calc(100%_-_4rem)] flex-col">
            <div className="flex-1 p-2">
              <Navigation mobile onNavigate={() => setMobileOpen(false)} />
            </div>
            <div className="border-t p-3">
              <SettingsLink mobile onNavigate={() => setMobileOpen(false)} />
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </>
  )
}
