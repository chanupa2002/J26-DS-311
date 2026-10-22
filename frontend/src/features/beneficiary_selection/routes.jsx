import { Navigate } from "react-router-dom"

import { ResearchPageFrame } from "./components/ResearchPageFrame"
import { CandidateScoringPage, SensitivityPage } from "./pages/BeneficiarySelectionPages"
import { HouseholdsPage, MethodPage } from "./pages/HouseholdScoresPage"
import { OverviewPage } from "./pages/OverviewPage"
import { RankingsPage } from "./pages/RankingsPage"

const frame = (page) => <ResearchPageFrame>{page}</ResearchPageFrame>

export const routes = [
  { path: "/beneficiary-selection", element: frame(<OverviewPage />), handle: { title: "Overview" } },
  { path: "/beneficiary-selection/households", element: frame(<HouseholdsPage />), handle: { title: "Household Scores" } },
  { path: "/beneficiary-selection/rankings", element: frame(<RankingsPage />), handle: { title: "Stage 6 Rankings" } },
  { path: "/beneficiary-selection/assess", element: frame(<CandidateScoringPage />), handle: { title: "Assess a Household" } },
  { path: "/beneficiary-selection/robustness", element: frame(<SensitivityPage />), handle: { title: "Robustness" } },
  { path: "/beneficiary-selection/method", element: frame(<MethodPage />), handle: { title: "Method & Limits" } },
  { path: "/beneficiary-selection/score", element: <Navigate to="/beneficiary-selection/assess?tab=single" replace />, handle: { title: "Assess a Household" } },
  { path: "/beneficiary-selection/bulk", element: <Navigate to="/beneficiary-selection/assess?tab=csv" replace />, handle: { title: "Assess a Household" } },
  { path: "/beneficiary-selection/summary", element: <Navigate to="/beneficiary-selection" replace />, handle: { title: "Overview" } },
  { path: "/beneficiary-selection/sensitivity", element: <Navigate to="/beneficiary-selection/robustness" replace />, handle: { title: "Robustness" } },
]
