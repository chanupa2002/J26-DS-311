import { useRef } from "react"

import { Badge } from "@/components/ui/badge"

import { HouseholdHeader, V2PageState, VisitForm, VisitResult } from "../components"
import { useV2Market, useV2Visit } from "../hooks"

export function CheckVisitV2Page() {
  const market = useV2Market(undefined)
  const visit = useV2Visit()
  const resultRef = useRef(null)
  const rows = market.data?.rows ?? []
  const districts = [...new Set(rows.map((row) => row.district))].sort()
  // UNASSIGNED is accepted by the API (scored with the general consumer-price series).
  const categories = [...[...new Set(rows.map((row) => row.category))].sort(), ...(rows.length ? ["UNASSIGNED"] : [])]

  const submit = (body) =>
    visit.mutate(body, {
      onSettled: () => requestAnimationFrame(() => resultRef.current?.focus()),
    })

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Score one monthly visit: current risk by rule, 3- and 6-month outlook, the reasons and the market level.
      </p>
      {market.isPending || market.isError ? (
        <V2PageState loading={market.isPending} error={market.error} rows={2} onRetry={() => market.refetch()} />
      ) : (
        <VisitForm districts={districts} categories={categories} onSubmit={submit} submitting={visit.isPending} />
      )}
      <section ref={resultRef} tabIndex={-1} aria-live="polite" aria-label="Result" className="space-y-4 outline-none">
        {visit.isPending && <V2PageState loading rows={2} />}
        {visit.isError && <V2PageState error={visit.error} />}
        {visit.isSuccess && (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="secondary">Result</Badge>
              <HouseholdHeader visit={visit.data} />
            </div>
            {visit.data.grant_status_label && (
              <p className="text-sm">
                <span className="text-muted-foreground">Samurdhi grant status: </span>
                {visit.data.grant_status_label}
              </p>
            )}
            <VisitResult visit={visit.data} />
          </>
        )}
      </section>
    </div>
  )
}
