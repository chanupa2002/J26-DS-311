import { Bar, BarChart, Cell, LabelList, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

import { wrapLabel } from "../utils"
import { categoryLabel, RISK_FILL_CLASS, RISK_ORDER } from "./v2format"

const NO_HOUSEHOLDS = "– no monitored households"

function ChartTip({ active, payload, unit = "households" }) {
  if (!active || !payload?.length) return null
  const item = payload[0].payload
  return (
    <div className="rounded-md border bg-popover px-2 py-1 text-xs text-popover-foreground shadow-md">
      <span className="font-medium">{item.name}</span>:{" "}
      {item.monitored === false ? "no monitored households" : `${item.value} ${unit}${item.total ? ` (of ${item.total} monitored)` : ""}`}
    </div>
  )
}

const AXIS_WIDTH = 112

/** Bar-end count for bars with a length (recharts draws no label for zero-length bars). */
function BarLabel({ x, y, width, height, index, data }) {
  const item = data[index]
  if (!item || x === undefined || !(item.value > 0)) return null
  return (
    <text x={x + width + 4} y={y + height / 2} dominantBaseline="central" fontSize={11} className="fill-foreground">
      {item.value}
    </text>
  )
}

/**
 * Axis label (the name), plus the label of rows without a bar, drawn at the bar baseline:
 * "0" for monitored rows with no High, a grey italic "– no monitored households" for empty rows.
 */
function NameTick({ x, y, payload, data }) {
  const item = data[payload.index]
  const lines = wrapLabel(payload.value, 18, 3)
  const empty = item?.monitored === false
  return (
    <g>
      <text x={x} y={y - ((lines.length - 1) * 11) / 2} textAnchor="end" dominantBaseline="central" fontSize={11} className="fill-muted-foreground">
        {lines.map((line, i) => (
          <tspan key={i} x={x} dy={i === 0 ? 0 : 11}>
            {line}
          </tspan>
        ))}
      </text>
      {item && !(item.value > 0) && (
        <text
          x={x + 8}
          y={y}
          dominantBaseline="central"
          fontSize={11}
          fontStyle={empty ? "italic" : undefined}
          className={empty ? "fill-muted-foreground" : "fill-foreground"}
        >
          {empty ? NO_HOUSEHOLDS : "0"}
        </text>
      )}
    </g>
  )
}

function countBy(rows, key, predicate) {
  const counts = new Map()
  for (const row of rows) counts.set(row[key], (counts.get(row[key]) || 0) + (predicate(row) ? 1 : 0))
  return [...counts].map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value || String(a.name).localeCompare(String(b.name)))
}

/** Donut of this month's risk counts; every slice is named with its count in the legend list. */
function RiskDonut({ rows }) {
  const data = RISK_ORDER.map((name) => ({ name, value: rows.filter((row) => row.current_risk === name).length }))
  const shown = data.filter((d) => d.value > 0)
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Risk this month</CardTitle>
        <CardDescription>{rows.length} households</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col items-center gap-4 sm:flex-row lg:flex-col">
        <div className="h-40 w-40 shrink-0" aria-hidden="true">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={shown} dataKey="value" nameKey="name" innerRadius="58%" outerRadius="95%" paddingAngle={2} stroke="none" isAnimationActive={false}>
                {shown.map((d) => (
                  <Cell key={d.name} className={RISK_FILL_CLASS[d.name]} />
                ))}
              </Pie>
              <Tooltip content={<ChartTip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <ul className="w-full max-w-56 space-y-1.5 text-sm">
          {data.map((d) => (
            <li key={d.name} className="flex items-center gap-2">
              <svg className="size-3 shrink-0" aria-hidden="true">
                <rect width="12" height="12" rx="3" className={RISK_FILL_CLASS[d.name]} />
              </svg>
              <span className="flex-1">{d.name}</span>
              <span className="font-medium tabular-nums">{d.value}</span>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  )
}

/** Horizontal bars: number of households that are High risk this month, per group. */
function HighBars({ title, description, data, note, maxHeight, axisWidth = AXIS_WIDTH }) {
  const row = data.length > 12 ? 24 : 30
  const height = Math.max(120, data.length * row + 16)
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="overflow-y-auto pr-1" style={maxHeight ? { maxHeight } : undefined}>
          <div style={{ height }} aria-hidden="true">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 0 }} barCategoryGap={4}>
                <XAxis type="number" hide allowDecimals={false} domain={[0, (max) => Math.max(1, max)]} />
                <YAxis type="category" dataKey="name" width={axisWidth} tick={<NameTick data={data} />} interval={0} tickLine={false} axisLine={false} />
                <Tooltip content={<ChartTip unit="High-risk households" />} cursor={{ className: "fill-muted" }} />
                <Bar dataKey="value" className={RISK_FILL_CLASS.High} radius={[0, 4, 4, 0]} isAnimationActive={false}>
                  {data.map((d) => (
                    <Cell key={d.name} className={d.monitored === false ? "fill-transparent" : RISK_FILL_CLASS.High} />
                  ))}
                  <LabelList dataKey="value" content={<BarLabel data={data} />} />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
        {note && <p className="mt-3 text-xs text-muted-foreground">{note}</p>}
        <table className="sr-only">
          <caption>{title}</caption>
          <tbody>
            {data.map((d) => (
              <tr key={d.name}>
                <th scope="row">{d.name}</th>
                <td>{d.monitored === false ? "no monitored households" : d.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  )
}

/**
 * High-risk count for every district in the market table (25), so empty districts stay visible.
 * Districts with households first (most High first), then districts without households (A–Z).
 */
function districtCounts(rows, districts, high) {
  const names = [...new Set([...districts, ...rows.map((row) => row.district)])]
  const items = names.map((name) => {
    const inDistrict = rows.filter((row) => row.district === name)
    return { name, monitored: inDistrict.length > 0, total: inDistrict.length, value: inDistrict.filter(high).length }
  })
  return [
    ...items.filter((d) => d.monitored).sort((a, b) => b.value - a.value || a.name.localeCompare(b.name)),
    ...items.filter((d) => !d.monitored).sort((a, b) => a.name.localeCompare(b.name)),
  ]
}

/** Overview of the selected month: households API rows; district names from the market table. */
export function HouseholdCharts({ rows, districts = [] }) {
  const high = (row) => row.current_risk === "High"
  const byDistrict = districtCounts(rows, districts, high)
  const monitoredDistricts = byDistrict.filter((d) => d.monitored).length
  const districtNote =
    byDistrict.length > monitoredDistricts
      ? `Simulated households are in ${monitoredDistricts} ${monitoredDistricts === 1 ? "district" : "districts"} only; real visits will fill the other districts.`
      : null
  const byLivelihood = countBy(rows, "category", high).map((d) => ({ ...d, name: categoryLabel(d.name) }))
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <RiskDonut rows={rows} />
      <HighBars
        title="High risk by district"
        description={`Households that are High risk this month, all ${byDistrict.length} districts`}
        data={byDistrict}
        note={districtNote}
        maxHeight={420}
        axisWidth={88}
      />
      <HighBars title="High risk by livelihood" description="Households that are High risk this month" data={byLivelihood} />
    </div>
  )
}
