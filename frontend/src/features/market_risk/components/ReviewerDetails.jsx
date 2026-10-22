import { ChevronDown } from "lucide-react"

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

import { ABOUT_DATA } from "../constants"
import { FeatureList } from "./FeatureList"
import { LimitationsList } from "./LimitationsList"
import { TradeOffTable } from "./TradeOffTable"

/** Page-level "Technical details": version trade-off, limitations and the model inputs. */
export function ReviewerDetails({ features }) {
  return (
    <Collapsible className="rounded-lg border">
      <CollapsibleTrigger className="group flex w-full items-center justify-between gap-3 px-4 py-3 text-left">
        <div className="space-y-0.5">
          <p className="text-sm font-medium">Technical details (for reviewers)</p>
          <p className="text-xs text-muted-foreground">About the data, version trade-off, limitations and the 53 model inputs.</p>
        </div>
        <ChevronDown className="size-4 shrink-0 transition-transform group-data-[state=open]:rotate-180" />
      </CollapsibleTrigger>
      <CollapsibleContent className="space-y-6 border-t p-4">
        <div className="space-y-2 text-sm">
          <p className="font-medium">About the data</p>
          {ABOUT_DATA.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </div>
        <TradeOffTable />
        <LimitationsList />
        <FeatureList features={features} />
      </CollapsibleContent>
    </Collapsible>
  )
}
