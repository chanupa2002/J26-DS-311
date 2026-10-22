import { DashboardPage, MonitoringPage } from "./pages"

export const routes = [
  { path: "/trust/monitoring", element: <MonitoringPage />, handle: { title: "Monitoring form" } },
  { path: "/trust/dashboard", element: <DashboardPage />, handle: { title: "Officer dashboard" } },
]
