import { createBrowserRouter } from "react-router-dom"

import { AppShell } from "@/app/AppShell"
import { DashboardPage } from "@/app/DashboardPage"
import { featureRoutes } from "@/app/features"
import { LoginPage } from "@/app/LoginPage"
import { NotFoundPage } from "@/app/NotFoundPage"
import { RequireAuth } from "@/app/RequireAuth"
import { RouteErrorBoundary } from "@/app/RouteErrorBoundary"
import { SettingsPage } from "@/app/SettingsPage"

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
    errorElement: <RouteErrorBoundary />,
  },
  {
    element: <RequireAuth />,
    errorElement: <RouteErrorBoundary />,
    children: [
      {
        element: <AppShell />,
        children: [
          {
            index: true,
            element: <DashboardPage />,
            handle: { title: "Dashboard" },
          },
          ...featureRoutes,
          {
            path: "/settings",
            element: <SettingsPage />,
            handle: { title: "Settings" },
          },
          {
            path: "*",
            element: <NotFoundPage />,
            handle: { title: "Page not found" },
          },
        ],
      },
    ],
  },
])
