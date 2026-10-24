export const MODEL1_TRAINED_DISTRICTS = ["Badulla", "Monaragala"]

const UNAVAILABLE_TEXT = new Set([
  "not available",
  "viability not available",
  "n/a",
  "none",
])

export function hasDisplayValue(value) {
  if (value === null || value === undefined) return false
  if (typeof value === "string") {
    const normalized = value.trim().toLowerCase()
    return normalized !== "" && !UNAVAILABLE_TEXT.has(normalized)
  }
  if (Array.isArray(value)) return value.some(hasDisplayValue)
  if (typeof value === "object") {
    return Object.values(value).some(hasDisplayValue)
  }
  return true
}

export function isUntrainedDistrict(district) {
  const normalizedDistrict = String(district ?? "")
    .trim()
    .toLowerCase()

  if (!normalizedDistrict) return false

  return !MODEL1_TRAINED_DISTRICTS.some(
    (trainedDistrict) => trainedDistrict.toLowerCase() === normalizedDistrict,
  )
}

export function titleCaseLivelihood(value) {
  return String(value || "")
    .toLocaleLowerCase("en")
    .replace(/\b\w/g, (letter) => letter.toLocaleUpperCase("en"))
}

export function displayValue(value) {
  if (value === null) return "—"
  if (typeof value === "boolean") return value ? "Yes" : "No"
  return String(value)
}

export function scoreOutOf100(value) {
  const number = Number(value)
  if (!Number.isFinite(number)) return 0
  return Math.min(100, Math.max(0, number <= 1 ? number * 100 : number))
}

export function cleanProfile(values) {
  return Object.fromEntries(
    Object.entries(values).filter(
      ([, value]) => value !== "" && value !== null && value !== undefined,
    ),
  )
}
