import {
  AssessPage,
  BeneficiariesPage,
  HistoryPage,
  PlanPage,
  RecommendPage,
  SwotPage,
} from "./pages"

export const routes = [
  {
    path: "/livelihood/beneficiaries",
    element: <BeneficiariesPage />,
    handle: { title: "Livelihood Beneficiaries" },
  },
  {
    path: "/livelihood/assess",
    element: <AssessPage />,
    handle: { title: "Assess" },
  },
  {
    path: "/livelihood/swot",
    element: <SwotPage />,
    handle: { title: "SWOT" },
  },
  {
    path: "/livelihood/recommend",
    element: <RecommendPage />,
    handle: { title: "Recommend" },
  },
  {
    path: "/livelihood/history",
    element: <HistoryPage />,
    handle: { title: "Assessment History" },
  },
  {
    path: "/livelihood/plan",
    element: <PlanPage />,
    handle: { title: "Plan" },
  },
]
