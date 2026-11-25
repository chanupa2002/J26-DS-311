import { SimulatedBadge } from "./SimulatedBadge"
import { categoryLabel, shortMonth } from "./v2format"

/** Identity line of a scored visit (not a page title). */
export function HouseholdHeader({ visit }) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
      <span className="text-base font-semibold">{visit.household_key || "Real visit"}</span>
      <span className="text-muted-foreground">
        {visit.district} · {categoryLabel(visit.category)} · {shortMonth(visit.monitoring_period)}
      </span>
      <SimulatedBadge isSynthetic={visit.is_synthetic} />
      {visit.note && <span className="text-muted-foreground">{visit.note}</span>}
    </div>
  )
}
