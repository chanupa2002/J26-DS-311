import { BellRing } from "lucide-react"

import { Badge } from "@/components/ui/badge"

/** true = needs attention (3-month alert), false = no, null = no alert level exists. */
export function AlertBadge({ alert }) {
  if (alert === true) {
    return (
      <Badge variant="destructive" className="gap-1 whitespace-nowrap">
        <BellRing className="size-3" aria-hidden="true" />
        Yes – needs attention
      </Badge>
    )
  }
  if (alert === false) return <Badge variant="outline">No</Badge>
  return (
    <Badge variant="outline" className="whitespace-nowrap border-dashed text-muted-foreground">
      No alert available
    </Badge>
  )
}
