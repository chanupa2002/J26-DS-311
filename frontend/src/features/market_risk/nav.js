import { ChartNoAxesCombined } from "lucide-react"

// Only the automatic monitoring pages. The manual-entry pages (v1 Risk Check / Future Risk,
// Check a visit) stay in the code but are not in the menu.
export const nav = {
  title: "Market Risk",
  icon: ChartNoAxesCombined,
  items: [
    { title: "Households", path: "/risk/v2/households" },
    { title: "Market pressure", path: "/risk/v2/market" },
    { title: "Model evidence", path: "/risk/v2/evidence" },
  ],
}
