import { ChevronDown } from "lucide-react"

import { EvidenceCard } from "@/components/explain/EvidenceCard"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

const QUADRANTS = [
  ["strengths", "Strengths", "border-emerald-500/30 bg-emerald-500/10"],
  ["weaknesses", "Weaknesses", "border-amber-500/30 bg-amber-500/10"],
  ["opportunities", "Opportunities", "border-sky-500/30 bg-sky-500/10"],
  ["threats", "Threats", "border-rose-500/30 bg-rose-500/10"],
]

function SwotItem({ item }) {
  return (
    <div className="space-y-2">
      <EvidenceCard
        text={item.text}
        source={item.source}
        strength={item.strength}
      />
      {item.evidence && (
        <Collapsible>
          <CollapsibleTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="group w-full justify-between"
            >
              Evidence
              <ChevronDown className="transition-transform group-data-[state=open]:rotate-180" />
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="rounded-md bg-muted/60 p-3 text-sm text-muted-foreground">
            {item.evidence}
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  )
}

export function SwotGrid({ swot }) {
  if (!swot) return null

  return (
    <section className="space-y-3">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
        SWOT
      </h3>
      <div className="grid gap-4 lg:grid-cols-2">
        {QUADRANTS.map(([key, title, colour]) => {
          const items = swot[key] || []
          return (
            <Card key={key}>
              <CardHeader className={`rounded-t-xl border-b ${colour}`}>
                <CardTitle>{title}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 pt-6">
                {items.length ? (
                  items.map((item, index) => (
                    <SwotItem key={`${item.text}-${index}`} item={item} />
                  ))
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No clear signal found in the data
                  </p>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>
    </section>
  )
}
