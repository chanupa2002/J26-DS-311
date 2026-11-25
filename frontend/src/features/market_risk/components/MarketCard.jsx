import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

import { MarketPill } from "./MarketPill"
import { shortMonth } from "./v2format"

/** Market price pressure for the household's livelihood and district (level from the API). */
export function MarketCard({ market }) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Market prices for this livelihood</CardTitle>
        <CardDescription>Did prices move unusually for this kind of business?</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="flex flex-wrap items-center gap-2">
          <MarketPill level={market.level} className="px-3 py-1 text-base" />
          <span>{market.level ? "price pressure" : "no price value for this month"}</span>
        </div>
        {market.price_month_used && (
          <p className="text-muted-foreground">
            Based on public prices for {shortMonth(market.price_month_used)}
            {market.series ? ` (${market.series})` : ""}.
          </p>
        )}
      </CardContent>
    </Card>
  )
}
