// Display helpers for the v2 pages. No risk logic or thresholds: values come from the API.

/** "AGRICULTURE & PLANTATION CROPS" -> "Agriculture & Plantation Crops" (display only). */
export function categoryLabel(category) {
  if (!category) return "—"
  return String(category)
    .toLowerCase()
    .replace(/(^|[\s(/-])([a-z])/g, (_, start, letter) => start + letter.toUpperCase())
    .replace(/\bAnd\b/g, "and")
}

/** "2026-06" -> "Jun 2026" */
export function shortMonth(month) {
  if (!/^\d{4}-\d{2}$/.test(String(month || ""))) return month || "—"
  const [year, number] = month.split("-").map(Number)
  return new Date(year, number - 1, 1).toLocaleString("en", { month: "short", year: "numeric" })
}

export function percent(value, digits = 0) {
  const number = Number(value)
  if (value === null || value === undefined || !Number.isFinite(number)) return "—"
  return `${(number * 100).toFixed(digits)}%`
}

/** A threshold or probability as the API gives it, rounded for reading (e.g. 0.475). */
export function decimal(value, digits = 3) {
  const number = Number(value)
  if (value === null || value === undefined || !Number.isFinite(number)) return "—"
  return number.toFixed(digits)
}

/** Market pressure in SD units: "+0.58 SD from normal". */
export function sdText(value) {
  const number = Number(value)
  if (value === null || value === undefined || !Number.isFinite(number)) return "No value"
  const sign = number > 0 ? "+" : number < 0 ? "−" : ""
  return `${sign}${Math.abs(number).toFixed(2)} SD from normal`
}

/** A SHAP contribution to P(High) in percentage points: "+4.2 pts". */
export function pointsText(contribution) {
  const number = Number(contribution) * 100
  if (!Number.isFinite(number)) return "—"
  const sign = number > 0 ? "+" : number < 0 ? "−" : ""
  return `${sign}${Math.abs(number).toFixed(1)} pts`
}

/** Display order of the risk classes on a chart axis (not a risk rule). */
export const RISK_AXIS = ["Low", "Medium", "High"]

export const METRIC_LABELS = {
  ROC_AUC: "ROC-AUC",
  balanced_accuracy: "Balanced accuracy",
}

// Style per level name that the API returns (presentation only, no cut-offs).
export const MARKET_LEVEL_CLASS = {
  Normal: "border-transparent bg-sky-100 text-sky-900 dark:bg-sky-900/50 dark:text-sky-100",
  Moderate: "border-transparent bg-amber-200 text-amber-950 dark:bg-amber-500/40 dark:text-amber-50",
  High: "border-transparent bg-red-600 text-white dark:bg-red-500/80",
}
export const MARKET_EMPTY_CLASS = "border-dashed bg-muted text-muted-foreground"

/**
 * Probability as a natural frequency (Gigerenzer & Hoffrage, 1995): 0.27 -> "about 3 in 10".
 * Plain rounding of P(High) × 10, no cut-offs.
 */
export function inTen(value) {
  const number = Number(value)
  if (value === null || value === undefined || !Number.isFinite(number)) return "—"
  const count = Math.round(number * 10)
  if (count === 0) return "less than 1 in 10"
  return `about ${count} in 10`
}

/** Risk class fills for charts (validated for colour-vision deficiency; always shown with text). */
export const RISK_FILL_CLASS = {
  High: "fill-red-600 dark:fill-red-500",
  Medium: "fill-amber-500",
  Low: "fill-emerald-600",
  Unassigned: "fill-gray-400 dark:fill-zinc-600",
}
export const RISK_ORDER = ["High", "Medium", "Low", "Unassigned"]

/**
 * Table order: needs attention first – 3-month alert, then High this month, then Unassigned
 * (form incomplete), then the rest; within a group the higher chance of High comes first.
 * Uses only the API fields (alert_3m, current_risk, p_high_3m).
 */
export function attentionRank(row) {
  if (row.alert_3m === true) return 0
  if (row.current_risk === "High") return 1
  if (row.current_risk === "Unassigned") return 2
  return 3
}
export function sortByAttention(rows) {
  return [...rows].sort(
    (a, b) => attentionRank(a) - attentionRank(b) || b.p_high_3m - a.p_high_3m || a.household_key.localeCompare(b.household_key),
  )
}
