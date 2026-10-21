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
