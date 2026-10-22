import { useState } from "react"

import { Button } from "@/components/ui/button"

import { BLANK_VALUE_TEXT, FACTOR_STRENGTH, FACTOR_TEXT, FACTORS_SHOWN, SHAP_COLORS } from "../constants"
import { featureValueText, pointsText, strengthWord } from "../utils"
import { FeatureName } from "./FeatureName"

/**
 * Officer view of high_risk_factors: plain label and value, a short bar (red raises, green
 * lowers), the effect on P(High) in whole points and a strength word. No numeric axis.
 */
export function FactorList({ factors = [] }) {
  const [showAll, setShowAll] = useState(false)
  if (!factors.length) return <p className="text-sm text-muted-foreground">No factors returned.</p>

  const sorted = [...factors].sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
  const largest = Math.abs(sorted[0].contribution) || 1
  const shown = showAll ? sorted : sorted.slice(0, FACTORS_SHOWN)

  return (
    <div className="space-y-3">
      <p className="text-sm font-medium">{FACTOR_TEXT.title}</p>
      <ul className="space-y-3">
        {shown.map((factor) => {
          const raises = factor.contribution > 0
          const share = Math.abs(factor.contribution) / largest
          return (
            <li key={factor.feature} className="grid gap-1 sm:grid-cols-[minmax(0,1fr)_minmax(0,14rem)] sm:items-center sm:gap-4">
              <div className="min-w-0 text-sm">
                <FeatureName name={factor.feature} className="font-medium" />
                <span className="text-muted-foreground">
                  : {featureValueText(factor.feature, factor.value, BLANK_VALUE_TEXT)}
                </span>
              </div>
              <div className="space-y-1">
                <div className="h-2 overflow-hidden rounded-full bg-muted" aria-hidden="true">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${Math.max(4, share * 100)}%`,
                      background: raises ? SHAP_COLORS.towardsHigh : SHAP_COLORS.awayFromHigh,
                    }}
                  />
                </div>
                <p className="flex flex-wrap justify-between gap-x-2 text-xs">
                  <span className={raises ? "text-red-700 dark:text-red-400" : "text-green-700 dark:text-green-400"}>
                    {raises ? FACTOR_TEXT.raises : FACTOR_TEXT.lowers} · {pointsText(factor.contribution)}
                  </span>
                  <span className="text-muted-foreground">{strengthWord(share, FACTOR_STRENGTH)}</span>
                </p>
              </div>
            </li>
          )
        })}
      </ul>
      {sorted.length > FACTORS_SHOWN && (
        <Button type="button" variant="outline" size="sm" onClick={() => setShowAll((open) => !open)}>
          {showAll ? FACTOR_TEXT.showFewer : FACTOR_TEXT.showAll(sorted.length)}
        </Button>
      )}
    </div>
  )
}
