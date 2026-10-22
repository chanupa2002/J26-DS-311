import { ArrowDownRight, ArrowUpRight } from "lucide-react"

import { BLANK_VALUE_TEXT, WHY_AWAY, WHY_TEXT, WHY_TOWARDS } from "../constants"
import { featureValueText, formatPercent } from "../utils"
import { FeatureName } from "./FeatureName"

function Reason({ factor, towards }) {
  const Icon = towards ? ArrowUpRight : ArrowDownRight
  return (
    <li className="flex items-start gap-2">
      <Icon className={towards ? "mt-0.5 size-4 shrink-0 text-red-600" : "mt-0.5 size-4 shrink-0 text-green-600"} />
      <span>
        <FeatureName name={factor.feature} className="font-medium" />:{" "}
        {featureValueText(factor.feature, factor.value, BLANK_VALUE_TEXT)} –{" "}
        {towards ? WHY_TEXT.towards : WHY_TEXT.away}
      </span>
    </li>
  )
}

/** Plain-language reasons from high_risk_factors (+ towards High, − away from High). */
export function WhyCard({ explanation }) {
  const factors = [...explanation.high_risk_factors].sort(
    (a, b) => Math.abs(b.contribution) - Math.abs(a.contribution),
  )
  const towards = factors.filter((factor) => factor.contribution > 0).slice(0, WHY_TOWARDS)
  const away = factors.filter((factor) => factor.contribution < 0).slice(0, WHY_AWAY)

  return (
    <div className="space-y-3 rounded-lg border bg-muted/30 p-4 text-sm">
      <p className="font-medium">{WHY_TEXT.title}</p>
      <p className="text-muted-foreground">
        The {explanation.horizon} model gives a {formatPercent(explanation.high_risk_probability)} chance
        of High risk ({explanation.predicted_risk} is the most likely class).
      </p>
      <ul className="space-y-1.5">
        {towards.map((factor) => (
          <Reason key={factor.feature} factor={factor} towards />
        ))}
        {!towards.length && <li className="text-muted-foreground">{WHY_TEXT.noTowards}</li>}
        {away.map((factor) => (
          <Reason key={factor.feature} factor={factor} towards={false} />
        ))}
        {!away.length && <li className="text-muted-foreground">{WHY_TEXT.noAway}</li>}
      </ul>
      <p className="text-xs text-muted-foreground">{WHY_TEXT.note}</p>
    </div>
  )
}
