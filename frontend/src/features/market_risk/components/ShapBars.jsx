import { ArrowDown, ArrowUp } from "lucide-react"
import { Bar, BarChart, Cell, ReferenceLine, ResponsiveContainer, XAxis, YAxis } from "recharts"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

import { SHAP_COLORS } from "../constants"
import { wrapLabel } from "../utils"
import { pointsText } from "./v2format"

const ROW = 52

function Tick({ x, y, payload }) {
  const lines = wrapLabel(payload.value, 20, 3)
  return (
    <text x={x} y={y - ((lines.length - 1) * 13) / 2 + 4} textAnchor="end" fontSize={11} className="fill-foreground">
      {lines.map((line, i) => (
        <tspan key={i} x={x} dy={i === 0 ? 0 : 13}>
          {line}
        </tspan>
      ))}
    </text>
  )
}

/** "Why this 3-month outlook?" – top SHAP factors, raising or lowering P(High). */
export function ShapBars({ factors = [] }) {
  const data = factors.map((factor) => ({ ...factor, name: factor.label }))
  const limit = Math.max(0.01, ...data.map((d) => Math.abs(d.contribution))) * 1.15
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Why this 3-month outlook?</CardTitle>
        <CardDescription>
          The 5 things that moved the chance of High risk most. Red bars to the right push it up, green bars to the left
          push it down.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {!data.length ? (
          <p className="text-muted-foreground">No explanation was returned.</p>
        ) : (
          <>
            <div aria-hidden="true" style={{ height: data.length * ROW + 24 }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data} layout="vertical" margin={{ top: 4, right: 12, bottom: 4, left: 4 }}>
                  <XAxis type="number" domain={[-limit, limit]} ticks={[-limit, -limit / 2, 0, limit / 2, limit]} tickFormatter={(v) => (v === 0 ? "0" : pointsText(v))} fontSize={10} />
                  <YAxis type="category" dataKey="name" width={150} tick={<Tick />} interval={0} />
                  <ReferenceLine x={0} className="stroke-foreground" strokeOpacity={0.6} />
                  <Bar dataKey="contribution" radius={3} isAnimationActive={false}>
                    {data.map((d) => (
                      <Cell key={d.feature} fill={d.contribution >= 0 ? SHAP_COLORS.towardsHigh : SHAP_COLORS.awayFromHigh} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <ol className="space-y-2">
              {data.map((d) => {
                const up = d.contribution >= 0
                const Icon = up ? ArrowUp : ArrowDown
                return (
                  <li key={d.feature} className="flex flex-wrap items-start gap-x-2 gap-y-1 border-b pb-2 last:border-0">
                    <Icon className="mt-0.5 size-4 shrink-0" style={{ color: up ? SHAP_COLORS.towardsHigh : SHAP_COLORS.awayFromHigh }} aria-hidden="true" />
                    <div className="min-w-0 flex-1">
                      <p className="font-medium">{d.label}</p>
                      <p className="text-muted-foreground">Value: {d.value}</p>
                    </div>
                    <Badge variant="secondary">{d.group}</Badge>
                    <span className="w-full text-xs sm:w-auto sm:text-sm">
                      {up ? "pushes the chance up" : "pushes the chance down"} ({pointsText(d.contribution)})
                    </span>
                  </li>
                )
              })}
            </ol>
          </>
        )}
      </CardContent>
    </Card>
  )
}
