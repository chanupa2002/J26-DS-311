import { Bar, BarChart, LabelList, ResponsiveContainer, XAxis, YAxis } from "recharts"

/** "A. Business status (t)" -> "Business status (t)" */
function groupName(text) {
  return String(text).replace(/^[A-Z]\.\s*/, "")
}

/** Share of total |SHAP| per factor group (3M model), as returned by the API. */
export function ShapGroupShare({ shares = [] }) {
  const data = shares.map((item) => ({ name: groupName(item.g), share: Number(item.share_pct) }))
  return (
    <>
      <div className="h-56" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ top: 0, right: 44, bottom: 0, left: 0 }}>
            <XAxis type="number" hide domain={[0, "dataMax"]} />
            <YAxis type="category" dataKey="name" width={150} fontSize={11} interval={0} />
            <Bar dataKey="share" className="fill-primary" radius={3} isAnimationActive={false}>
              <LabelList dataKey="share" position="right" fontSize={11} formatter={(v) => `${v}%`} className="fill-foreground" />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <ul className="sr-only">
        {data.map((item) => (
          <li key={item.name}>
            {item.name}: {item.share}%
          </li>
        ))}
      </ul>
    </>
  )
}
