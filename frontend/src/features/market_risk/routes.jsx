import { OverviewPage, RiskCheckPage } from "./pages"

export const routes = [
  {
    path: "/risk/overview",
    element: <OverviewPage />,
    handle: { title: "Overview" },
  },
  {
    path: "/risk/check",
    element: <RiskCheckPage />,
    handle: { title: "Risk Check" },
  },
]
