import { ClipboardList } from "lucide-react"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

import { RiskPill } from "./RiskPill"

/** This month's risk, worked out automatically from the visit form (not a prediction). */
export function CurrentRiskCard({ currentRisk }) {
  const unassigned = currentRisk.risk_class === "Unassigned"
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Risk this month</CardTitle>
        <CardDescription>Worked out from this month&apos;s visit form.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <RiskPill riskClass={currentRisk.risk_class} size="lg" />
        {unassigned && (
          <p className="flex items-start gap-2 rounded-md border border-dashed p-2 font-medium">
            <ClipboardList className="mt-0.5 size-4 shrink-0" aria-hidden="true" />
            Form incomplete – ask the SDO to complete the visit form.
          </p>
        )}
        <div>
          <p className="mb-1 font-medium">Why</p>
          <ul className="list-disc space-y-0.5 pl-5">
            {currentRisk.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </div>
      </CardContent>
    </Card>
  )
}
