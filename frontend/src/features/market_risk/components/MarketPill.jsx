import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

import { MARKET_EMPTY_CLASS, MARKET_LEVEL_CLASS } from "./v2format"

/** Market pressure level pill; null = no market value ("–", never a guessed level). */
export function MarketPill({ level, className }) {
  if (!level) {
    return (
      <Badge variant="outline" className={cn(MARKET_EMPTY_CLASS, className)} title="No market value">
        <span aria-hidden="true">–</span>
        <span className="sr-only">No market value</span>
      </Badge>
    )
  }
  return <Badge className={cn(MARKET_LEVEL_CLASS[level] || MARKET_EMPTY_CLASS, className)}>{level}</Badge>
}
