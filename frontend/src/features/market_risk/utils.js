import { UNAVAILABLE_MESSAGE_PREFIX } from "./constants"

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
  if (message.startsWith(UNAVAILABLE_MESSAGE_PREFIX)) return "unavailable"
  if (error instanceof TypeError || /failed to fetch|networkerror/i.test(message)) {
    return "network"
  }
  return "invalid"
}
