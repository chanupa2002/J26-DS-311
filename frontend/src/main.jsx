import "@fontsource-variable/inter"
import { StrictMode } from "react"
import { createRoot } from "react-dom/client"
import { RouterProvider } from "react-router-dom"

import { AppProviders } from "@/app/providers"
import { router } from "@/app/router"
import "@/index.css"
import { applyTheme, getInitialTheme } from "@/lib/theme"

applyTheme(getInitialTheme())

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  </StrictMode>,
)
