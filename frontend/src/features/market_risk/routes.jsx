import { Navigate } from "react-router-dom"

import {
  CheckVisitV2Page,
  FutureRiskPage,
  HouseholdDetailV2Page,
  HouseholdsV2Page,
  MarketPressurePage,
  ModelEvidencePage,
  RiskCheckPage,
} from "./pages"

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
  // v2: monthly monitoring after the Samurdhi grant (backend /api/risk/v2).
  {
    path: "/risk/v2/households",
    element: <HouseholdsV2Page />,
    handle: { title: "Households" },
  },
  {
    path: "/risk/v2/household/:householdKey",
    element: <HouseholdDetailV2Page />,
    handle: { title: "Household detail" },
  },
  {
    path: "/risk/v2/check",
    element: <CheckVisitV2Page />,
    handle: { title: "Check a visit (v2)" },
  },
  {
    path: "/risk/v2/market",
    element: <MarketPressurePage />,
    handle: { title: "Market pressure" },
  },
  {
    path: "/risk/v2/evidence",
    element: <ModelEvidencePage />,
    handle: { title: "Model evidence" },
  },
  // Old links open the automatic Households page instead of a blank page.
  {
    path: "/risk/overview",
    element: <Navigate to="/risk/v2/households" replace />,
    handle: { title: "Households" },
  },
  {
    path: "/risk",
    element: <Navigate to="/risk/v2/households" replace />,
    handle: { title: "Households" },
  },
]
