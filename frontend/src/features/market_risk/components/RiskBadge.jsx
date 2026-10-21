import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

import { RISK_BADGE_CLASS } from "../constants"

/** @param {{ riskClass: "Low" | "Medium" | "High" | "Unassigned", size?: "default" | "lg", className?: string }} props */
export function RiskBadge({ riskClass, size = "default", className }) {
  return (
    <Badge
      className={cn(
        RISK_BADGE_CLASS[riskClass] || RISK_BADGE_CLASS.Unassigned,
        size === "lg" && "px-3 py-1 text-base",
        className,
      )}
    >
      {riskClass}
    </Badge>
  )
}
