import { RiskBadge } from "./RiskBadge"

/** Risk class pill (Low / Medium / High / Unassigned). The class word is always shown. */
export function RiskPill({ riskClass, size, className }) {
  if (!riskClass) return <span className="text-muted-foreground">—</span>
  return <RiskBadge riskClass={riskClass} size={size} className={className} />
}
