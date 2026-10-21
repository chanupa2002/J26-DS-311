import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"
import { I18nextProvider } from "react-i18next"

import { Toaster } from "@/components/ui/sonner"
import { TooltipProvider } from "@/components/ui/tooltip"
import i18n from "@/i18n"
import {
  applyTheme,
  getInitialTheme,
  saveTheme,
  ThemeContext,
} from "@/lib/theme"

export function AppProviders({ children }) {
  const [theme, setTheme] = useState(getInitialTheme)
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: { retry: 1, refetchOnWindowFocus: false },
        },
      }),
  )
  const themeValue = useMemo(
    () => ({
      theme,
      toggleTheme: () =>
        setTheme((current) => (current === "dark" ? "light" : "dark")),
    }),
    [theme],
  )

  useEffect(() => {
    applyTheme(theme)
    saveTheme(theme)
  }, [theme])

  return (
    <ThemeContext.Provider value={themeValue}>
      <I18nextProvider i18n={i18n}>
        <QueryClientProvider client={queryClient}>
          <TooltipProvider delayDuration={200}>
            {children}
            <Toaster />
          </TooltipProvider>
        </QueryClientProvider>
      </I18nextProvider>
    </ThemeContext.Provider>
  )
}
