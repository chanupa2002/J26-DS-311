import { UsersRound } from "lucide-react"

export const nav = {
  title: "Beneficiary Selection",
  icon: UsersRound,
  items: [
    { title: "Overview", path: "/beneficiary-selection" },
    { title: "Household Scores", path: "/beneficiary-selection/households" },
    { title: "Stage 6 Rankings", path: "/beneficiary-selection/rankings" },
    { title: "Assess a Household", path: "/beneficiary-selection/assess" },
    { title: "Robustness", path: "/beneficiary-selection/robustness" },
    { title: "Method & Limits", path: "/beneficiary-selection/method" },
  ],
}
