import { FlaskConical, ShieldCheck } from "lucide-react"

import { Badge } from "@/components/ui/badge"

/** "Simulated" for synthetic data (always shown), "Real" otherwise. */
export function SimulatedBadge({ isSynthetic }) {
  if (isSynthetic) {
    return (
      <Badge variant="outline" className="gap-1 border-violet-400 text-violet-800 dark:border-violet-400/60 dark:text-violet-200">
        <FlaskConical className="size-3" aria-hidden="true" />
        Simulated
      </Badge>
    )
  }
  return (
    <Badge variant="outline" className="gap-1">
      <ShieldCheck className="size-3" aria-hidden="true" />
      Real
    </Badge>
  )
}
