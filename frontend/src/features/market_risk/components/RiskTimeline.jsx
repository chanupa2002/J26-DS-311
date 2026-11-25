import { BellRing } from "lucide-react"
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

import { SHAP_COLORS } from "../constants"
import { AlertBadge } from "./AlertBadge"
import { MarketPill } from "./MarketPill"
import { ProbabilityBar } from "./ProbabilityBar"
import { RiskPill } from "./RiskPill"
import { inTen, RISK_AXIS, shortMonth } from "./v2format"

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const point = payload[0].payload
  return (
    <div className="space-y-0.5 rounded-md border bg-popover p-2 text-xs text-popover-foreground shadow-md">
      <p className="font-medium">{shortMonth(point.monitoring_period)}</p>
      <p>Risk this month: {point.current_risk}</p>
      <p>
        Expected in 3 months: {point.predicted_3m} (chance of High {inTen(point.p_high_3m)})
      </p>
      {point.alert_3m === true && <p className="font-medium">Needs attention</p>}
    </div>
  )
}

const ALERT_COLOR = SHAP_COLORS.towardsHigh

/** Point marker: a red triangle in alert months, a plain dot otherwise (shape + colour, not colour only). */
function MonthDot({ cx, cy, payload }) {
  if (cx === undefined || cy === undefined || payload?.level === null) return null
  if (payload.alert_3m === true) {
    return <path d={`M ${cx} ${cy - 7} L ${cx + 6} ${cy + 4} L ${cx - 6} ${cy + 4} Z`} fill={ALERT_COLOR} className="stroke-background" strokeWidth={1.5} />
  }
  return <circle cx={cx} cy={cy} r={4} className="fill-primary stroke-background" strokeWidth={2} />
}

/** "Risk over the months": step line of this month's risk, alert months marked, then the table. */
export function RiskTimeline({ timeline = [] }) {
  const data = timeline.map((point) => ({
    ...point,
    month: shortMonth(point.monitoring_period),
    level: RISK_AXIS.includes(point.current_risk) ? RISK_AXIS.indexOf(point.current_risk) : null,
  }))
  const alertMonths = data.filter((point) => point.alert_3m === true)
  const gaps = data.some((point) => point.level === null)
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Risk over the months</CardTitle>
        <CardDescription>
          Risk at each monthly visit, oldest first.
          {gaps && " A gap means the form was incomplete that month (Unassigned)."}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="h-48" role="img" aria-label="Risk at each monthly visit; the same values are in the table below.">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 12, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-border" />
              <XAxis dataKey="month" fontSize={11} interval="preserveStartEnd" tickLine={false} />
              <YAxis
                domain={[0, RISK_AXIS.length - 1]}
                ticks={RISK_AXIS.map((_, i) => i)}
                tickFormatter={(i) => RISK_AXIS[i]}
                width={58}
                fontSize={11}
                tickLine={false}
                axisLine={false}
              />
              {alertMonths.map((point) => (
                <ReferenceLine
                  key={point.month}
                  x={point.month}
                  stroke={ALERT_COLOR}
                  strokeOpacity={0.6}
                  strokeDasharray="4 3"
                />
              ))}
              <Tooltip content={<ChartTooltip />} />
              <Line
                type="stepAfter"
                dataKey="level"
                className="stroke-primary"
                stroke="currentColor"
                strokeWidth={2}
                dot={<MonthDot />}
                activeDot={{ r: 5 }}
                connectNulls={false}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
        {alertMonths.length > 0 && (
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <BellRing className="size-3.5 shrink-0" aria-hidden="true" />
            <svg className="size-3 shrink-0" viewBox="0 0 12 12" aria-hidden="true">
              <path d="M 6 0 L 12 11 L 0 11 Z" fill={ALERT_COLOR} />
            </svg>
            Red triangle and dashed line = the household needed attention that month (3-month alert).
          </p>
        )}
        <Table className="min-w-[620px]">
          <TableHeader>
            <TableRow>
              <TableHead>Month</TableHead>
              <TableHead>Risk this month</TableHead>
              <TableHead>Expected in 3 months</TableHead>
              <TableHead>Chance of High risk</TableHead>
              <TableHead>Needs attention?</TableHead>
              <TableHead>Market prices</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {timeline.map((point) => (
              <TableRow key={point.monitoring_period}>
                <TableCell className="whitespace-nowrap font-medium">{shortMonth(point.monitoring_period)}</TableCell>
                <TableCell>
                  <RiskPill riskClass={point.current_risk} />
                </TableCell>
                <TableCell>
                  <RiskPill riskClass={point.predicted_3m} />
                </TableCell>
                <TableCell className="min-w-36">
                  <ProbabilityBar value={point.p_high_3m} compact />
                </TableCell>
                <TableCell>
                  <AlertBadge alert={point.alert_3m} />
                </TableCell>
                <TableCell>
                  <MarketPill level={point.market_level} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
