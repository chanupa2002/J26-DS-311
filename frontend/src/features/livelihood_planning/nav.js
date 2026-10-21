import { Sprout } from "lucide-react"

export const nav = {
  title: "Livelihood Planning",
  icon: Sprout,
  items: [
    { title: "Beneficiaries", path: "/livelihood/beneficiaries" },
    { title: "Assess", path: "/livelihood/assess" },
    { title: "SWOT", path: "/livelihood/swot" },
    { title: "Recommend", path: "/livelihood/recommend" },
    { title: "History", path: "/livelihood/history" },
    { title: "Plan", path: "/livelihood/plan", disabled: true },
  ],
}
