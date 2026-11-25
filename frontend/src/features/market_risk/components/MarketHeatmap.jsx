import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { cn } from "@/lib/utils"

import { categoryLabel, MARKET_EMPTY_CLASS, MARKET_LEVEL_CLASS, sdText, shortMonth } from "./v2format"

/** Levels in the order the API rows use them; unknown levels are appended (never invented). */
function levelsOf(rows) {
  const order = ["Normal", "Moderate", "High"]
  const found = [...new Set(rows.map((row) => row.market_pressure_level).filter(Boolean))]
  return [...order.filter((level) => found.includes(level)), ...found.filter((level) => !order.includes(level))]
}

export function MarketLegend({ rows }) {
  return (
    <ul className="flex flex-wrap items-center gap-3 text-xs" aria-label="Legend">
      {levelsOf(rows).map((level) => (
        <li key={level} className="flex items-center gap-1.5">
          <span className={cn("inline-block rounded px-1.5 py-0.5 font-medium", MARKET_LEVEL_CLASS[level] || MARKET_EMPTY_CLASS)}>{level}</span>
        </li>
      ))}
      <li className="flex items-center gap-1.5">
        <span className={cn("inline-block rounded border px-1.5 py-0.5", MARKET_EMPTY_CLASS)}>–</span>
        No value (not enough price history)
      </li>
    </ul>
  )
}

/** 25 districts × 9 livelihoods coloured by the API level, with the level word in every cell. */
export function MarketHeatmap({ rows }) {
  const districts = [...new Set(rows.map((row) => row.district))].sort()
  const categories = [...new Set(rows.map((row) => row.category))].sort()
  const cell = new Map(rows.map((row) => [`${row.district}|${row.category}`, row]))
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[820px] border-separate border-spacing-1 text-xs">
        <caption className="sr-only">Market pressure level by district and livelihood</caption>
        <thead>
          <tr>
            <th scope="col" className="sticky left-0 z-10 bg-card p-1 text-left font-medium">
              District
            </th>
            {categories.map((category) => (
              <th key={category} scope="col" className="p-1 align-bottom font-medium">
                {categoryLabel(category)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {districts.map((district) => (
            <tr key={district}>
              <th scope="row" className="sticky left-0 z-10 bg-card p-1 text-left font-medium whitespace-nowrap">
                {district}
              </th>
              {categories.map((category) => {
                const row = cell.get(`${district}|${category}`)
                const level = row?.market_pressure_level
                return (
                  <td key={category} className="p-0">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <button
                          type="button"
                          className={cn(
                            "w-full rounded border px-1 py-1.5 text-center font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1",
                            level ? MARKET_LEVEL_CLASS[level] || MARKET_EMPTY_CLASS : MARKET_EMPTY_CLASS,
                          )}
                          aria-label={`${district}, ${categoryLabel(category)}: ${level || "no value"}`}
                        >
                          {level || "–"}
                        </button>
                      </TooltipTrigger>
                      <TooltipContent className="max-w-xs space-y-0.5 text-xs">
                        <p className="font-medium">
                          {district} · {categoryLabel(category)}
                        </p>
                        <p>Level: {level || "no value"}</p>
                        <p>Pressure: {sdText(row?.market_pressure)}</p>
                        <p>Price month used: {row?.price_month_used ? shortMonth(row.price_month_used) : "—"}</p>
                        <p>Series: {row?.series || "—"}</p>
                      </TooltipContent>
                    </Tooltip>
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
