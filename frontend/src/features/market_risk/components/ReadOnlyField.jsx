import { Info } from "lucide-react"

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"

import { featureLabel } from "../utils"

/**
 * A calculated or auto-filled value shown like a field, but not editable. `tooltip` explains
 * where it comes from; `note` is the small text under it ("Auto-calculated" / "Auto-filled").
 * `countAsFilled` is read by FeatureForm only.
 */
export function ReadOnlyField({ name, text, tooltip, muted = false, note = "Auto-calculated" }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5 text-sm font-medium leading-snug">
        <span title={name}>{featureLabel(name)}</span>
        {tooltip && (
          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                className="rounded-sm text-muted-foreground hover:text-foreground"
                aria-label={`Where "${featureLabel(name)}" comes from`}
              >
                <Info className="size-3.5" />
              </button>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">{tooltip}</TooltipContent>
          </Tooltip>
        )}
      </div>
      <div
        role="status"
        aria-live="polite"
        className={`flex h-9 items-center rounded-md border border-dashed bg-muted/40 px-3 text-sm ${muted ? "text-muted-foreground" : ""}`}
      >
        {text}
      </div>
      <p className="text-[11px] text-muted-foreground">{note}</p>
    </div>
  )
}
