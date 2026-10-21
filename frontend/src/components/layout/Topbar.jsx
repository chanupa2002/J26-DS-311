import { ChevronDown, LogOut, Moon, Sun } from "lucide-react"
import { useMatches, useNavigate } from "react-router-dom"

import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { logout } from "@/lib/auth"
import { useTheme } from "@/lib/theme"

export function Topbar() {
  const matches = useMatches()
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()
  const pageTitle =
    [...matches].reverse().find((match) => match.handle?.title)?.handle
      ?.title || "Dashboard"

  const signOut = () => {
    logout()
    navigate("/login", { replace: true })
  }

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b bg-background/95 px-4 backdrop-blur sm:px-6">
      <SidebarTrigger mobile className="md:hidden" />
      <SidebarTrigger className="hidden md:inline-flex" />
      <h2 className="min-w-0 flex-1 truncate font-semibold">{pageTitle}</h2>

      <Button
        type="button"
        variant="ghost"
        size="icon"
        onClick={toggleTheme}
        aria-label={theme === "dark" ? "Use light theme" : "Use dark theme"}
      >
        {theme === "dark" ? <Sun /> : <Moon />}
      </Button>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="h-9 gap-2 px-2">
            <Avatar>
              <AvatarFallback>AD</AvatarFallback>
            </Avatar>
            <span className="hidden sm:inline">Admin</span>
            <ChevronDown className="size-3.5 opacity-60" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>Administrator</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onSelect={signOut}>
            <LogOut />
            Logout
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}
