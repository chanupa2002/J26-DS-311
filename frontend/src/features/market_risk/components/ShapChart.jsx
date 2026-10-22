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

import { BLANK_VALUE_TEXT, SHAP_COLORS } from "../constants"
import { featureLabel, featureValueText, formatSigned, wrapLabel } from "../utils"

const ROW_HEIGHT = 52
const LABEL_WIDTH = 168
const LINE_HEIGHT = 14

/** Two-line label: short plain label, then the value used, so nothing is cut off. */
function FactorTick({ x, y, payload, data }) {
  const factor = data[payload.index]
  if (!factor) return null
  const lines = wrapLabel(factor.label, 24, 2)
  const all = [...lines, factor.valueShort]
  const top = y - ((all.length - 1) * LINE_HEIGHT) / 2
  return (
    <text x={x} y={top} textAnchor="end" fontSize={12} className="fill-foreground">
      {all.map((line, i) => (
        <tspan
          key={i}
          x={x}
          dy={i === 0 ? 4 : LINE_HEIGHT}
          className={i === all.length - 1 ? "fill-muted-foreground" : undefined}
          fontSize={i === all.length - 1 ? 11 : 12}
        >
          {line}
        </tspan>
      ))}
    </text>
  )
}

function FactorTooltip({ active, payload }) {
  if (!active || !payload?.length) return null
  const factor = payload[0].payload
  return (
    <div className="max-w-xs space-y-1 rounded-md border bg-popover p-3 text-xs text-popover-foreground shadow-md">
      <p className="font-medium">{factor.label}</p>
      <p>Value: {factor.valueLong}</p>
      <p>
        SHAP value (effect on P(High)): {formatSigned(factor.contribution, 4)} ·{" "}
        {factor.contribution >= 0 ? "towards High" : "away from High"}
      </p>
      <p className="text-muted-foreground">Model input: {factor.feature}</p>
    </div>
  )
}

/** "nice" symmetric limit for the x-axis, so 0 is in the middle. */
function axisLimit(maxAbs) {
  if (!(maxAbs > 0)) return 0.01
  const padded = maxAbs * 1.15
  const step = 10 ** Math.floor(Math.log10(padded))
  return Math.ceil(padded / step) * step
}

/** Horizontal bars of high_risk_factors, largest first: + (red) towards High, − (green) away. */
export function ShapChart({ factors = [] }) {
  if (!factors.length) {
    return <p className="text-sm text-muted-foreground">No factors returned.</p>
  }

  const data = [...factors]
    .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
    .map((factor) => ({
      ...factor,
      label: featureLabel(factor.feature),
      valueShort: featureValueText(factor.feature, factor.value, "not answered"),
      valueLong: featureValueText(factor.feature, factor.value, BLANK_VALUE_TEXT),
    }))
  const limit = axisLimit(Math.max(...data.map((factor) => Math.abs(factor.contribution))))
  const ticks = [-limit, -limit / 2, 0, limit / 2, limit]

  return (
    <div className="space-y-2">
      <div style={{ height: data.length * ROW_HEIGHT + 40 }} className="w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 12, right: 24, bottom: 4, left: 4 }}
            barCategoryGap="28%"
          >
            <CartesianGrid horizontal={false} strokeDasharray="3 3" className="stroke-border" />
            <XAxis
              type="number"
              domain={[-limit, limit]}
              ticks={ticks}
              allowDataOverflow={false}
              tickFormatter={(value) => formatSigned(value, 3)}
              tick={{ fontSize: 11, fill: "currentColor" }}
              className="text-muted-foreground"
            />
            <YAxis
              type="category"
              dataKey="label"
              width={LABEL_WIDTH}
              interval={0}
              tick={<FactorTick data={data} />}
              tickLine={false}
            />
            <ReferenceLine x={0} className="stroke-muted-foreground" />
            <Tooltip content={<FactorTooltip />} cursor={{ fillOpacity: 0.08 }} />
            <Bar dataKey="contribution" radius={3} isAnimationActive={false} maxBarSize={22}>
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
