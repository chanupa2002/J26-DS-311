import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import { SHAP_COLORS } from "../constants"
import { formatSigned } from "../utils"

const LABEL_LENGTH = 34

function shortLabel(label) {
  const text = String(label || "")
  return text.length > LABEL_LENGTH ? `${text.slice(0, LABEL_LENGTH - 1)}…` : text
}

function FactorTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const factor = payload[0].payload
  return (
    <div className="max-w-xs space-y-1 rounded-md border bg-popover p-3 text-xs text-popover-foreground shadow-md">
      <p className="font-medium">{factor.label}</p>
      <p className="font-mono text-muted-foreground">{factor.feature}</p>
      <p>Value used: {factor.value === null ? "blank (median filled in)" : String(factor.value)}</p>
      <p>
        Contribution to P(High): {formatSigned(factor.contribution, 4)} ·{" "}
        {factor.contribution >= 0 ? "towards High" : "away from High"}
      </p>
    </div>
  )
}

/** Horizontal bars of high_risk_factors: + (red) pushes towards High, − (green) away. */
export function ShapChart({ factors = [] }) {
  if (!factors.length) {
    return <p className="text-sm text-muted-foreground">No factors returned.</p>
  }

  const data = factors.map((factor) => ({ ...factor, shortLabel: shortLabel(factor.label) }))

  return (
    <div className="space-y-2">
      <div style={{ height: data.length * 44 + 48 }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
            <CartesianGrid horizontal={false} strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              type="number"
              tickFormatter={(value) => formatSigned(value, 3)}
              tick={{ fontSize: 11, fill: "currentColor" }}
              className="text-muted-foreground"
            />
            <YAxis
              type="category"
              dataKey="shortLabel"
              width={190}
              tick={{ fontSize: 12, fill: "currentColor" }}
              className="text-foreground"
            />
            <ReferenceLine x={0} className="stroke-muted-foreground" />
            <Tooltip content={<FactorTooltip />} cursor={{ fillOpacity: 0.08 }} />
            <Bar dataKey="contribution" radius={3} isAnimationActive={false}>
              {data.map((factor) => (
                <Cell
                  key={factor.feature}
                  fill={factor.contribution >= 0 ? SHAP_COLORS.towardsHigh : SHAP_COLORS.awayFromHigh}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-wrap gap-4 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-sm" style={{ background: SHAP_COLORS.towardsHigh }} />
          Pushes towards High
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-sm" style={{ background: SHAP_COLORS.awayFromHigh }} />
          Pushes away from High
        </span>
      </div>
    </div>
  )
}
