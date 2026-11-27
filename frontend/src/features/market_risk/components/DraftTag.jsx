import { PencilRuler } from "lucide-react"

/** "Draft" until the supervisor validates the rule table (icon + text, not colour only). */
export function DraftTag() {
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-dashed px-1.5 py-0.5 text-xs font-medium normal-case tracking-normal text-foreground">
      <PencilRuler className="size-3" aria-hidden="true" />
      Draft
    </span>
  )
}
