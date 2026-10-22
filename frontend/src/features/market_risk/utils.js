import {
  BLANK,
  FEATURE_LABELS,
  FEATURE_OPTIONS,
  FEATURE_UNITS,
  PREVIOUS_VISIT_ANSWERS,
  UNAVAILABLE_MESSAGE_PREFIXES,
} from "./constants"

/** Select values ("1" / "0" / "blank") -> /identify body (1 / 0 / null). */
export function toSignals(formValues) {
  return Object.fromEntries(
    Object.entries(formValues).map(([key, value]) => [
      key,
      value === BLANK ? null : Number(value),
    ]),
  )
}

/** Backend reasons use "->"; show an arrow instead. */
export function formatReason(reason) {
  return String(reason).replaceAll("->", "→")
}

export function formatMetric(value, digits = 3) {
  const number = Number(value)
  if (value === null || value === undefined || !Number.isFinite(number)) {
    return "—"
  }
  return number.toFixed(digits)
}

export function formatPercent(value, digits = 1) {
  const number = Number(value)
  if (value === null || value === undefined || !Number.isFinite(number)) {
    return "—"
  }
  return `${(number * 100).toFixed(digits)}%`
}

export function formatSigned(value, digits = 3) {
  const number = Number(value)
  if (!Number.isFinite(number)) return "—"
  return `${number > 0 ? "+" : number < 0 ? "−" : ""}${Math.abs(number).toFixed(digits)}`
}

export function formatDateTime(value) {
  if (!value) return "—"
  return String(value).replace("T", " ").slice(0, 16)
}

export function statusLabel(status) {
  return status === "READY" ? "Ready" : "Validation pending"
}

/** data_basis "... panel (70 households, 9 categories)" -> "70 households, 9 categories" */
export function trainingDataLabel(dataBasis) {
  if (!dataBasis) return "—"
  const inBrackets = String(dataBasis).match(/\(([^)]+)\)/)
  return inBrackets ? inBrackets[1] : String(dataBasis)
}

export function splitReasons(reason) {
  return String(reason || "")
    .split(";")
    .map((part) => part.trim())
    .filter(Boolean)
}

/**
 * api() keeps only the message, not the HTTP status (FRONTEND_PLAN.md §5):
 * 503 is recognised by the backend's fixed message, a failed fetch by TypeError.
 * @returns {"unavailable" | "network" | "invalid"}
 */
export function errorKind(error) {
  const message = String(error?.message || "")
  if (UNAVAILABLE_MESSAGE_PREFIXES.some((prefix) => message.startsWith(prefix))) return "unavailable"
  if (error instanceof TypeError || /failed to fetch|networkerror/i.test(message)) {
    return "network"
  }
  return "invalid"
}

// ------------------------------------------------------------ Future Risk ----

/** Form values are strings ("" = blank); this builds an empty form for the given feature names. */
export function emptyFeatureForm(featureNames) {
  return Object.fromEntries(featureNames.map((name) => [name, ""]))
}

/** Feature object (numbers / strings / null) -> form strings. */
export function featuresToForm(featureNames, features) {
  return Object.fromEntries(
    featureNames.map((name) => {
      const value = features?.[name]
      return [name, value === null || value === undefined ? "" : String(value)]
    }),
  )
}

/** Last Risk Check signals -> the 3 answer features as form strings ("1" / "0" / ""). */
export function answersFromRiskCheck(signals, signalMap) {
  const form = {}
  for (const [key, feature] of Object.entries(signalMap)) {
    if (feature === "F_Market_Stress_Any_t") continue
    form[feature] = signals?.[key] === null || signals?.[key] === undefined ? "" : String(signals[key])
  }
  return form
}

export function timeLabel(epochMs) {
  return new Date(epochMs).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })
}

/**
 * Form strings -> { features, invalid }. All keys are always sent; blanks become null.
 * Numeric fields that are not finite numbers are returned in `invalid`.
 */
export function formToFeatures(featureNames, categorical, values) {
  const features = {}
  const invalid = []
  for (const name of featureNames) {
    const raw = String(values[name] ?? "").trim()
    if (raw === "") {
      features[name] = null
    } else if (categorical.includes(name)) {
      features[name] = raw
    } else {
      const number = Number(raw)
      if (Number.isFinite(number)) features[name] = number
      else {
        features[name] = null
        invalid.push(name)
      }
    }
  }
  return { features, invalid }
}

export function countFilled(values) {
  return Object.values(values).filter((value) => String(value ?? "").trim() !== "")
    .length
}

// ---------------------------------------------------------------- History ----

const DATE_PATTERN = /^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$/

/** A real calendar date "YYYY-MM-DD" (rejects e.g. 2026-02-30). */
export function isValidDate(value) {
  if (!DATE_PATTERN.test(String(value || ""))) return false
  const [year, month, day] = value.split("-").map(Number)
  const date = new Date(Date.UTC(year, month - 1, day))
  return date.getUTCMonth() === month - 1 && date.getUTCDate() === day
}

/** "2026-09" -> "2026-09-30" */
export function lastDayOfMonth(month) {
  const [year, number] = month.split("-").map(Number)
  return `${month}-${String(new Date(Date.UTC(year, number, 0)).getUTCDate()).padStart(2, "0")}`
}

export function monthLabel(month) {
  const [year, number] = month.split("-").map(Number)
  return new Date(year, number - 1, 1).toLocaleString("en", { month: "long", year: "numeric" })
}

/** The `count` months before `month` ("YYYY-MM"), newest first. */
export function monthsBefore(month, count) {
  const [year, number] = month.split("-").map(Number)
  return Array.from({ length: count }, (_, i) => {
    const date = new Date(Date.UTC(year, number - 2 - i, 1))
    return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, "0")}`
  })
}

function toAnswer(value) {
  return value === BLANK || value === "" || value === undefined ? null : Number(value)
}

/** Form value of a negatively worded F_* signal ("1"/"0"/"") -> positively worded answer. */
function currentAnswer(formValue, invert) {
  const value = toAnswer(formValue)
  return value === null || !invert ? value : 1 - value
}

/**
 * Builds the /history-features body. Returns { request, problems, status }:
 * status "unknown" (no history given), "incomplete" (fix the problems first) or "ready".
 * problems: { visitDate?, grantDate?, rows: { [rowId]: message }, section? }.
 */
export function buildHistoryRequest({ values, visitDate, grantDate, firstVisit, visits, answerMap }) {
  const problems = { rows: {} }
  const month = isValidDate(visitDate) ? visitDate.slice(0, 7) : null
  if (!month) return { request: null, problems, status: visitDate ? "incomplete" : "unknown" }
  if (grantDate && !isValidDate(grantDate)) problems.grantDate = "Enter a full date (YYYY-MM-DD)."
  else if (grantDate && grantDate > visitDate) problems.grantDate = "The grant date must not be after the visit date."
  if (!firstVisit && !visits.length) return { request: null, problems, status: "unknown" }

  const seen = new Set()
  for (const visit of firstVisit ? [] : visits) {
    if (!visit.month) problems.rows[visit.id] = "Choose the month of this visit."
    else if (visit.month >= month) problems.rows[visit.id] = "This month is not before the visit month."
    else if (seen.has(visit.month)) problems.rows[visit.id] = "Another visit already uses this month."
    seen.add(visit.month)
  }
  const current = Object.fromEntries(
    Object.entries(answerMap).map(([field, { feature, invert }]) => [field, currentAnswer(values[feature], invert)]),
  )
  const request = {
    current_visit: { visit_date: visitDate, ...current, grant_date: grantDate || null },
    previous_visits: firstVisit
      ? []
      : visits.map(({ month: visitMonth, business_running, profit_last_month, progressing_well, market_stress }) => ({
          month: visitMonth,
          business_running: toAnswer(business_running),
          profit_last_month: toAnswer(profit_last_month),
          progressing_well: toAnswer(progressing_well),
          market_stress: toAnswer(market_stress),
        })),
  }
  const ok = !problems.grantDate && !Object.keys(problems.rows).length
  return { request: ok ? request : null, problems, status: ok ? "ready" : "incomplete" }
}

/**
 * api() keeps only the 422 message (not `loc`), so the message is matched to a field:
 * the backend names grant_date / visit_date, or lists the months of the bad visits.
 */
export function historyErrorTargets(message, visits) {
  const text = String(message || "")
  const targets = { rows: {} }
  if (/grant_date/.test(text)) targets.grantDate = text
  else if (/visit_date/.test(text) && !/previous_visits/.test(text)) targets.visitDate = text
  const months = text.match(/\d{4}-\d{2}/g) || []
  if (/previous_visits/.test(text)) {
    for (const visit of visits) if (months.includes(visit.month)) targets.rows[visit.id] = text
  }
  if (!targets.grantDate && !targets.visitDate && !Object.keys(targets.rows).length) targets.section = text
  return targets
}

let nextVisitId = 1

/** An empty previous-visit row (answers "Not answered"). */
export function newPreviousVisit() {
  return {
    id: `visit-${nextVisitId++}`,
    open: true, // UI only: the row is being edited (not sent to the backend)
    month: "",
    ...Object.fromEntries(PREVIOUS_VISIT_ANSWERS.map(({ key }) => [key, BLANK])),
  }
}

// ----------------------------------------------------------------- Labels ----

/** Short plain label for a feature (falls back to the name). */
export function featureLabel(name) {
  return FEATURE_LABELS[name] || name
}

/** A feature value in words: Yes/No, Low/Medium/High, units; `blank` for null. */
export function featureValueText(name, value, blank = "blank") {
  if (value === null || value === undefined || value === "") return blank
  if (typeof value === "string" && !Number.isFinite(Number(value))) return value
  const number = Number(value)
  const option = FEATURE_OPTIONS[name]?.options.find((item) => Number(item.value) === number)
  if (option) return option.label
  const unit = FEATURE_UNITS[name] || {}
  if (unit.percentOf1) return `${Math.round(number * 100)}%`
  const rounded = Number(number.toFixed(unit.digits ?? 2))
  if (unit.riskScale) {
    const classes = ["Low", "Medium", "High"]
    const lower = Math.floor(rounded)
    const word = Number.isInteger(rounded)
      ? classes[rounded]
      : `between ${classes[lower]} and ${classes[lower + 1]}`
    return word ? `${rounded} (${word})` : String(rounded)
  }
  const sign = unit.signed && rounded > 0 ? "+" : ""
  return `${unit.prefix || ""}${sign}${rounded}${unit.suffix || ""}`
}

/** Split a label into at most `maxLines` lines of about `width` characters (whole words). */
export function wrapLabel(text, width = 20, maxLines = 2) {
  const lines = []
  for (const word of String(text).split(" ")) {
    const last = lines[lines.length - 1]
    if (last !== undefined && `${last} ${word}`.length <= width) lines[lines.length - 1] = `${last} ${word}`
    else lines.push(word)
  }
  if (lines.length <= maxLines) return lines
  return [...lines.slice(0, maxLines - 1), lines.slice(maxLines - 1).join(" ")]
}

/** Text -> parts, where every F_* name becomes { feature } (to show its label). */
export function splitFeatureNames(text) {
  return String(text)
    .split(/(F_[A-Za-z0-9_]+)/)
    .filter(Boolean)
    .map((part) => (/^F_[A-Za-z0-9_]+$/.test(part) ? { feature: part } : part))
}

// --------------------------------------------------------------- Overview ----

/** A share 0..1 as "N in M": 1 in 2 / 1 or 2 in 3 / 1 or 3 in 4 when close, else "N in 10". */
export function shareInWords(share) {
  const value = Number(share)
  if (!Number.isFinite(value)) return null
  for (const denominator of [2, 3, 4]) {
    const numerator = Math.round(value * denominator)
    if (numerator > 0 && numerator < denominator && Math.abs(value - numerator / denominator) <= 0.02) {
      return `${numerator} in ${denominator}`
    }
  }
  return `${Math.round(value * 10)} in 10`
}

/** Model Macro-F1 vs the "same as last visit" baseline: "better" / "about the same" / "worse". */
export function comparedWithBaseline(model, baseline, margin) {
  if (!Number.isFinite(Number(model)) || !Number.isFinite(Number(baseline))) return null
  const difference = Number(model) - Number(baseline)
  if (difference > margin) return "better"
  if (difference < -margin) return "worse"
  return "about the same"
}

// ------------------------------------------------- Derived current fields ----

/**
 * "Any market problem reported" from its 3 parts: "1" if any is Yes, "0" if all are No,
 * else "". Until a part is answered, an overall answer from Risk Check (`fallback`) is used.
 */
export function deriveMarketProblem(values, parts, fallback = "") {
  const answers = parts.map((name) => String(values[name] ?? ""))
  if (answers.every((answer) => answer === "") && fallback !== "") return { value: fallback, fromRiskCheck: true }
  if (answers.includes("1")) return { value: "1", fromRiskCheck: false }
  if (answers.every((answer) => answer === "0")) return { value: "0", fromRiskCheck: false }
  return { value: "", fromRiskCheck: false }
}

/** /identify response -> the 3 derived numeric features (Unassigned -> null). */
export function riskFeaturesFromIdentify(result, riskOrd) {
  if (!result) return { F_Risk_Ord_t: null, F_Risk_Signal_Count_t: null, F_Risk_Unknown_t: null }
  return {
    F_Risk_Ord_t: riskOrd[result.risk_class] ?? null,
    F_Risk_Signal_Count_t: result.signal_count,
    F_Risk_Unknown_t: result.unknown_count,
  }
}

// ------------------------------------------------------------ Factor list ----

/** A SHAP contribution to P(High) in whole percentage points: "+3 points", "<1 point". */
export function pointsText(contribution) {
  const points = Math.abs(Number(contribution)) * 100
  if (!Number.isFinite(points)) return "—"
  if (points < 0.5) return "<1 point"
  const rounded = Math.round(points)
  return `${contribution > 0 ? "+" : "−"}${rounded} ${rounded === 1 ? "point" : "points"}`
}

/** Strength word for |share| of the largest factor (share in 0..1). */
export function strengthWord(share, levels) {
  return levels.find((level) => share >= level.min)?.label || levels[levels.length - 1].label
}
