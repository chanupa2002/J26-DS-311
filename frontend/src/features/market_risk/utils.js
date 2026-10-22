import { BLANK, PREVIOUS_VISIT_ANSWERS, UNAVAILABLE_MESSAGE_PREFIXES } from "./constants"

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

/** "SYNTHETIC panel (70 households, 9 categories)" -> "70 households, 9 categories" */
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

/** Risk Check router state -> partial feature object (7 features), or null. */
export function featuresFromRiskCheck(state, signalMap, countMap) {
  if (!state?.signals) return null
  const prefill = {}
  for (const [key, feature] of Object.entries(signalMap)) {
    prefill[feature] = state.signals[key] ?? null
  }
  for (const [key, feature] of Object.entries(countMap)) {
    prefill[feature] = state[key] ?? null
  }
  return prefill
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
