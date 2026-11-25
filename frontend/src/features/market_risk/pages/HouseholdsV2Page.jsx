import { useMemo, useState } from "react"
import { useSearchParams } from "react-router-dom"

import { Card, CardContent } from "@/components/ui/card"

import {
  categoryLabel,
  FilterChips,
  HouseholdCharts,
  HouseholdsTable,
  KpiCard,
  MonthSelect,
  percent,
  SimulatedBadge,
  sortByAttention,
  V2PageState,
} from "../components"
import { useV2Evidence, useV2Households, useV2Market } from "../hooks"

const FILTERS = [
  { value: "All", label: "All", test: () => true },
  { value: "Attention", label: "Needs attention", test: (row) => row.alert_3m === true },
  { value: "High", label: "High", test: (row) => row.current_risk === "High" },
  { value: "Medium", label: "Medium", test: (row) => row.current_risk === "Medium" },
  { value: "Low", label: "Low", test: (row) => row.current_risk === "Low" },
  { value: "Unassigned", label: "Unassigned", test: (row) => row.current_risk === "Unassigned" },
]

export function HouseholdsV2Page() {
  const [params, setParams] = useSearchParams()
  const month = params.get("month") || undefined
  const [filter, setFilter] = useState("All")

  const households = useV2Households(month)
  const market = useV2Market(month)
  const latestMarket = useV2Market(undefined)
  const evidence = useV2Evidence()

  const rows = useMemo(() => sortByAttention(households.data?.households ?? []), [households.data])
  const shown = rows.filter(FILTERS.find((item) => item.value === filter).test)
  const count = (predicate) => rows.filter(predicate).length
  const alertThreshold = evidence.data?.alert_thresholds?.["3M"]

  const marketRows = market.data?.rows ?? []
  const categories = [...new Set(marketRows.map((row) => row.category))]
  const highCategories = categories.filter((category) =>
    marketRows.some((row) => row.category === category && row.market_pressure_level === "High"),
  )

  const changeMonth = (value) => {
    setFilter("All")
    setParams(value ? { month: value } : {})
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <MonthSelect
            months={latestMarket.data?.available_months ?? []}
            value={month ?? households.data?.month ?? latestMarket.data?.month}
            onChange={changeMonth}
          />
          {households.data && <SimulatedBadge isSynthetic={households.data.is_synthetic} />}
          {households.data?.note && <span className="text-sm text-muted-foreground">{households.data.note}</span>}
        </div>
      </div>

      {households.isPending || households.isError ? (
        <V2PageState loading={households.isPending} error={households.error} onRetry={() => households.refetch()} />
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard label="High risk this month" value={count((row) => row.current_risk === "High")} hint="From this month's visit forms" />
            <KpiCard label="Need attention (3-month alert)" value={count((row) => row.alert_3m === true)} hint="Likely to be High risk in 3 months" />
            <KpiCard label="Form incomplete (Unassigned)" value={count((row) => row.current_risk === "Unassigned")} hint="Ask the SDO to complete the form" />
            <KpiCard
              label="Livelihoods with High market pressure"
              value={market.data ? `${highCategories.length} of ${categories.length}` : "—"}
              hint={
                market.isError
                  ? market.error.message
                  : highCategories.length
                    ? `${highCategories.map(categoryLabel).join(", ")} (in some districts)`
                    : "None this month"
              }
            />
          </div>

          <HouseholdCharts rows={rows} districts={[...new Set(marketRows.map((row) => row.district))]} />

          <FilterChips
            label="Show"
            value={filter}
            onChange={setFilter}
            options={FILTERS.map((item) => ({ value: item.value, label: item.label, count: count(item.test) }))}
          />
          <p className="text-xs text-muted-foreground">
            Households that need attention are listed first, then High risk this month, then incomplete forms.
          </p>

          {shown.length ? (
            <Card>
              <CardContent className="p-0 sm:p-2">
                <HouseholdsTable households={shown} alertThreshold={alertThreshold} />
              </CardContent>
            </Card>
          ) : (
            <V2PageState empty emptyMessage="No households in this group for this month." />
          )}

          <p className="text-xs text-muted-foreground">
            {alertThreshold === undefined
              ? evidence.isError
                ? `Alert level could not be loaded: ${evidence.error.message}`
                : "Loading the alert level…"
              : alertThreshold === null
                ? "No 3-month alert level is set."
                : `"Needs attention" means the model's chance of High risk in 3 months is ${percent(alertThreshold)} or more – a level learned from past data (Youden's J). The dashed marker on each bar shows it.`}
          </p>
        </>
      )}
    </div>
  )
}
