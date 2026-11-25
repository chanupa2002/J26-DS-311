import { CartesianGrid, LabelList, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"

import { inTen, percent } from "./v2format"

// One line per starting class. Hue follows the class (same validated palette as the risk charts),
// and each line also has its own dash pattern and a direct label, so colour is never the only signal.
const LINE_STYLE = {
  High: { color: "#dc2626", dash: undefined, label: "Starts High" },
  Medium: { color: "#f59e0b", dash: "8 4", label: "Starts Medium" },
  Low: { color: "#059669", dash: "2 4", label: "Starts Low" },
}
const LINE_ORDER = ["High", "Medium", "Low"]

function monthsText(months) {
  return `after ${months} ${months === 1 ? "month" : "months"}`
}

function ChartTip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div className="space-y-0.5 rounded-md border bg-popover p-2 text-xs text-popover-foreground shadow-md">
      <p className="font-medium">Chance of High {monthsText(label)}</p>
      {LINE_ORDER.map((name) => {
        const item = payload.find((entry) => entry.dataKey === name)
        if (!item) return null
        return (
          <p key={name}>
            {LINE_STYLE[name].label}: {inTen(item.value)} ({percent(item.value, 1)})
          </p>
        )
      })}
    </div>
  )
}

// Direct labels sit at the second point (month 2), away from the axis and before the lines come
// together. The top line is labelled above, the bottom line below, and the middle line on the side
// with more room, so labels never sit on another line.
function DirectLabel({ x, y, index, name, at, below }) {
  if (index !== at || x === undefined || y === undefined) return null
  return (
    <text x={x + 6} y={below ? y + 16 : y - 9} fontSize={11} className="fill-foreground">
      {name}
    </text>
  )
}

function labelSides(row) {
  const sorted = [...LINE_ORDER].sort((a, b) => (row?.[b] ?? 0) - (row?.[a] ?? 0))
  const [top, middle, bottom] = sorted
  const sides = { [top]: false, [bottom]: true }
  sides[middle] = (row?.[top] ?? 0) - (row?.[middle] ?? 0) < (row?.[middle] ?? 0) - (row?.[bottom] ?? 0)
  return sides
}

function LegendKey({ name }) {
  const style = LINE_STYLE[name]
  return (
    <li className="flex items-center gap-1.5">
      <svg width="28" height="8" aria-hidden="true">
        <line x1="0" y1="4" x2="28" y2="4" stroke={style.color} strokeWidth="2" strokeDasharray={style.dash} />
      </svg>
      {style.label}
    </li>
  )
}

/**
 * "Chance of High risk after 1–6 months", one line per starting class (P^k from /model/evidence).
 * The lines come together: after a few months the starting class says little.
 */
export function ChanceAfterChart({ rows = [] }) {
  const at = Math.min(1, rows.length - 1)
  const below = labelSides(rows[at])
  return (
    <div className="space-y-3">
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-xs" aria-label="Lines">
        {LINE_ORDER.map((name) => (
          <LegendKey key={name} name={name} />
        ))}
      </ul>
      <div className="h-64" role="img" aria-label="Chance of High risk after 1 to 6 months for households starting Low, Medium or High; the same values are in the table below.">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={rows} margin={{ top: 16, right: 16, bottom: 16, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} className="stroke-border" />
            <XAxis
              dataKey="months"
              fontSize={11}
              tickLine={false}
              label={{ value: "Months from now", position: "insideBottom", offset: -8, fontSize: 11 }}
            />
            <YAxis
              domain={[0, 1]}
              ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]}
              tickFormatter={(value) => `${Math.round(value * 10)} in 10`}
              width={60}
              fontSize={11}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<ChartTip />} />
            {LINE_ORDER.map((name) => (
              <Line
                key={name}
                dataKey={name}
                name={LINE_STYLE[name].label}
                stroke={LINE_STYLE[name].color}
                strokeWidth={2}
                strokeDasharray={LINE_STYLE[name].dash}
                dot={{ r: 4, fill: LINE_STYLE[name].color, strokeWidth: 0 }}
                activeDot={{ r: 6 }}
                isAnimationActive={false}
              >
                <LabelList dataKey={name} content={<DirectLabel name={name} at={at} below={below[name]} />} />
              </Line>
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
      <table className="sr-only">
        <caption>Chance of High risk after 1 to 6 months, by risk class this month</caption>
        <thead>
          <tr>
            <th>Months from now</th>
            {LINE_ORDER.map((name) => (
              <th key={name}>{LINE_STYLE[name].label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.months}>
              <td>{row.months}</td>
              {LINE_ORDER.map((name) => (
                <td key={name}>{inTen(row[name])} ({percent(row[name], 1)})</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
