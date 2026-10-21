import { Badge } from "@/components/ui/badge"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

/** @param {{ show?: boolean }} props */
export function WeakSignalTag({ show = true }) {
  if (!show) return null
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge variant="outline">Weak signal</Badge>
      </TooltipTrigger>
      <TooltipContent>
        This evidence should be interpreted cautiously.
      </TooltipContent>
    </Tooltip>
  )
}
