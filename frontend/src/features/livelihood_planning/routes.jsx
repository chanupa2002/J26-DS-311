import {
  AssessPage,
  BeneficiariesPage,
  HistoryPage,
  RecommendPage,
  SwotPage,
} from "./pages"

export const routes = [
  {
    path: "/livelihood/beneficiaries",
    element: <BeneficiariesPage />,
    handle: { title: "Beneficiaries" },
  },
  {
    path: "/livelihood/assess",
    element: <AssessPage />,
    handle: { title: "Assess" },
  },
  {
    path: "/livelihood/assess/:beneficiaryId",
    element: <AssessPage />,
    handle: { title: "Assess" },
  },
  {
    path: "/livelihood/recommend",
    element: <RecommendPage />,
    handle: { title: "Recommend" },
  },
  {
    path: "/livelihood/swot",
    element: <SwotPage />,
    handle: { title: "SWOT" },
  },
  {
    path: "/livelihood/history",
    element: <HistoryPage />,
    handle: { title: "History" },
  },
]
