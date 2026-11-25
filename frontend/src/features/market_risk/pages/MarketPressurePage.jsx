import { useSearchParams } from "react-router-dom"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

import { MarketHeatmap, MarketLegend, MonthSelect, shortMonth, SimulatedBadge, V2PageState } from "../components"
import { useV2Market } from "../hooks"

export function MarketPressurePage() {
  const [params, setParams] = useSearchParams()
  const month = params.get("month") || undefined
  const market = useV2Market(month)
  const latest = useV2Market(undefined)
  const data = market.data

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <MonthSelect
          months={latest.data?.available_months ?? []}
          value={month ?? data?.month ?? latest.data?.month}
          onChange={(value) => setParams(value ? { month: value } : {})}
        />
        {data && <SimulatedBadge isSynthetic={data.is_synthetic} />}
        {data?.note && <span className="text-sm text-muted-foreground">{data.note}</span>}
      </div>
      {market.isPending || market.isError ? (
        <V2PageState loading={market.isPending} error={market.error} onRetry={() => market.refetch()} />
      ) : !data.rows.length ? (
        <V2PageState empty emptyMessage="No market rows for this month." />
      ) : (
        <Card>
          <CardHeader className="space-y-3 pb-3">
            <CardTitle className="text-base">
              {data.count} district × livelihood cells, {shortMonth(data.month)}
            </CardTitle>
            <CardDescription>Hover or focus a cell for its value, price month and price series.</CardDescription>
            <MarketLegend rows={data.rows} />
          </CardHeader>
          <CardContent>
            <MarketHeatmap rows={data.rows} />
          </CardContent>
        </Card>
      )}
      <p className="text-xs text-muted-foreground">
        Levels follow the FAO Indicator of Food Price Anomalies (SDG 2.c.1): how unusual this month&apos;s price change is
        compared with earlier months, in standard deviations. The level of each cell is the one the API returns. A
        &quot;–&quot; means there is not enough price history for a value.
      </p>
    </div>
  )
}
