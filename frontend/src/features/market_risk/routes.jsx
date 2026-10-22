import { Navigate } from "react-router-dom"

import { FutureRiskPage, RiskCheckPage } from "./pages"

export const routes = [
  {
    path: "/risk/check",
    element: <RiskCheckPage />,
    handle: { title: "Risk Check" },
  },
  {
    path: "/risk/future",
    element: <FutureRiskPage />,
    handle: { title: "Future Risk" },
  },
  // The Overview page was removed (O3): old links go to Risk Check instead of a blank page.
  {
    path: "/risk/overview",
    element: <Navigate to="/risk/check" replace />,
    handle: { title: "Risk Check" },
  },
  {
    path: "/risk",
    element: <Navigate to="/risk/check" replace />,
    handle: { title: "Risk Check" },
  },
]
