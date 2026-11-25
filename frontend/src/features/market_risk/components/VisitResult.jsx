import { CurrentRiskCard } from "./CurrentRiskCard"
import { FutureRiskCard } from "./FutureRiskCard"
import { HowThisWorks } from "./HowThisWorks"
import { MarketCard } from "./MarketCard"
import { ShapBars } from "./ShapBars"
import { WarningsNote } from "./WarningsNote"

/** The result cards of one scored visit; research notes are in "How this works" (set `notes={false}` to place it elsewhere). */
export function VisitResult({ visit, notes = true }) {
  return (
    <div className="space-y-4">
      <WarningsNote warnings={visit.warnings} />
      <div className="grid gap-4 lg:grid-cols-3">
        <CurrentRiskCard currentRisk={visit.current_risk} />
        <FutureRiskCard predictions={visit.predictions} />
        <MarketCard market={visit.market} />
      </div>
      <ShapBars factors={visit.shap_top_factors} />
      {notes && <HowThisWorks visit={visit} />}
    </div>
  )
}
