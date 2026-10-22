import { BLANK, UNAVAILABLE_MESSAGE_PREFIXES } from "./constants"

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
