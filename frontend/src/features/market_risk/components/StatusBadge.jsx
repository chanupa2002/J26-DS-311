import { Badge } from "@/components/ui/badge"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

import { statusLabel } from "../utils"

/** Friendly status label; the raw backend model_status stays in the tooltip. */
export function StatusBadge({ status, prefix }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant="outline"
          className="border-amber-500/50 text-amber-800 dark:text-amber-300"
        >
          {prefix && `${prefix}: `}
          {statusLabel(status)}
        </Badge>
      </TooltipTrigger>
      <TooltipContent>model_status: {status || "unknown"}</TooltipContent>
    </Tooltip>
  )
}
