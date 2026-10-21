import { Badge } from "@/components/ui/badge"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

/** @param {{ level: "low" | "normal" }} props */
export function ConfidenceBadge({ level }) {
  const low = level === "low"
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge variant={low ? "destructive" : "secondary"}>
          {low ? "Low confidence" : "Normal confidence"}
        </Badge>
      </TooltipTrigger>
      <TooltipContent>
        {low
          ? "Review the supporting evidence before deciding."
          : "The available signals are sufficiently consistent."}
      </TooltipContent>
    </Tooltip>
  )
}
