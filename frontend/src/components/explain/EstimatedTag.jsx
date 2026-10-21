import { Badge } from "@/components/ui/badge"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

/** @param {{ estimated?: boolean }} props */
export function EstimatedTag({ estimated = true }) {
  if (!estimated) return null
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge variant="outline">Estimated</Badge>
      </TooltipTrigger>
      <TooltipContent>
        District-level monitoring data was not available.
      </TooltipContent>
    </Tooltip>
  )
}
