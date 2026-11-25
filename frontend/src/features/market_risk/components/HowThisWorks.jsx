import { ChevronDown } from "lucide-react"

import { Card } from "@/components/ui/card"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"

import { percent, sdText } from "./v2format"

/** Research and method notes, closed by default. Values come from the API response. */
export function HowThisWorks({ visit }) {
  const m3 = visit.predictions?.["3M"]
  const market = visit.market ?? {}
  return (
    <Card>
      <Collapsible>
        <CollapsibleTrigger className="group flex w-full items-center justify-between rounded-xl p-4 text-left font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
          How this works
          <ChevronDown className="size-4 transition-transform group-data-[state=open]:rotate-180" aria-hidden="true" />
        </CollapsibleTrigger>
        <CollapsibleContent>
          <ul className="list-disc space-y-2 px-4 pb-4 pl-9 text-sm text-muted-foreground">
            <li>
              <span className="text-foreground">Risk this month</span> comes from a counting rule on the visit form
              (business running, profit, coach view, market problems): {visit.current_risk?.rule_version}.
              {" "}
              {visit.current_risk?.signal_count} warning {visit.current_risk?.signal_count === 1 ? "signal was" : "signals were"} found this month.
            </li>
            <li>
              <span className="text-foreground">Expected risk</span> comes from random-forest models trained on earlier
              visits. Chances are shown as &quot;about N in 10&quot; (Gigerenzer &amp; Hoffrage, 1995); the exact percentage is
              in the tooltip.
              {m3?.alert_threshold !== null && m3?.alert_threshold !== undefined &&
                ` "Needs attention" means the 3-month chance is ${percent(m3.alert_threshold, 1)} or more, a level learned from training data with Youden's J (1950).`}
              {" "}The 6-month outlook did not beat &quot;risk stays the same&quot; in testing, so it never raises an alert.
            </li>
            <li>
              <span className="text-foreground">Why this outlook</span> uses SHAP values (Lundberg &amp; Lee, 2017). Factors
              are grouped as Business, Household shock, History, Market and Current risk, following Dercon (2002). The model
              learned from simulated data, so the reasons show how the system explains its outlook, not real-world causes.
            </li>
            <li>
              <span className="text-foreground">Market prices</span> use the FAO Indicator of Food Price Anomalies (SDG
              2.c.1): how unusual the price change is compared with earlier months
              {market.pressure !== null && market.pressure !== undefined ? ` (here ${sdText(market.pressure)})` : ""}.
              {market.basis ? ` Basis: ${market.basis}.` : ""}
            </li>
          </ul>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
