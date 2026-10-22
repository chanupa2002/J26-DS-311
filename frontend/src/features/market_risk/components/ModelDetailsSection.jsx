import { ChevronDown } from "lucide-react"

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

import { ABOUT_DATA, MODEL_DETAILS_TEXT } from "../constants"
import { FeatureList } from "./FeatureList"
import { LimitationsList } from "./LimitationsList"
import { ModelMetricsCard } from "./ModelMetricsCard"
import { TradeOffTable } from "./TradeOffTable"

/**
 * Collapsed reviewer section at the bottom of Future Risk (moved from the former Overview page):
 * per model the reliability sentences and technical details, then the data note, version
 * trade-off, limitations and the 53 inputs.
 */
export function ModelDetailsSection({ models = [], features = [] }) {
  return (
    <Collapsible className="rounded-lg border">
      <CollapsibleTrigger className="group flex w-full items-center justify-between gap-3 px-4 py-3 text-left">
        <div className="space-y-0.5">
          <p className="text-sm font-medium">{MODEL_DETAILS_TEXT.title}</p>
          <p className="text-xs text-muted-foreground">{MODEL_DETAILS_TEXT.subtitle}</p>
        </div>
        <ChevronDown className="size-4 shrink-0 transition-transform group-data-[state=open]:rotate-180" />
      </CollapsibleTrigger>
      <CollapsibleContent className="space-y-6 border-t p-4">
        <div className="grid gap-6 lg:grid-cols-2">
          {models.map((model) => (
            <ModelMetricsCard key={model.horizon} model={model} />
          ))}
        </div>
        <p className="-mt-3 text-xs text-muted-foreground">{MODEL_DETAILS_TEXT.reliabilityFooter}</p>
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
