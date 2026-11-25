import { ArrowLeft } from "lucide-react"
import { Link, useParams } from "react-router-dom"

import { Button } from "@/components/ui/button"

import { HouseholdHeader, HowThisWorks, RiskTimeline, StepStrip, V2PageState, VisitResult } from "../components"
import { useV2Household } from "../hooks"

export function HouseholdDetailV2Page() {
  const { householdKey } = useParams()
  const household = useV2Household(householdKey)
  const data = household.data
  const visit = data?.latest_visit

  return (
    <div className="space-y-4">
      <Button asChild variant="ghost" size="sm" className="-ml-2">
        <Link to="/risk/v2/households">
          <ArrowLeft className="size-4" aria-hidden="true" />
          Households
        </Link>
      </Button>
      {household.isPending || household.isError ? (
        <V2PageState loading={household.isPending} error={household.error} onRetry={() => household.refetch()} />
      ) : (
        <>
          <HouseholdHeader visit={{ ...visit, is_synthetic: data.is_synthetic, note: data.note }} />
          <StepStrip
            category={visit.category}
            grantStatusLabel={visit.grant_status_label}
            visits={data.timeline.length}
            latestMonth={visit.monitoring_period}
          />
          <VisitResult visit={visit} notes={false} />
          <RiskTimeline timeline={data.timeline} />
          <HowThisWorks visit={visit} />
        </>
      )}
    </div>
  )
}
