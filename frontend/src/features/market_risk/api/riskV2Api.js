import { api } from "@/lib/api"

import { BASE_PATH } from "../constants"

const V2 = `${BASE_PATH}/v2`

function withMonth(path, month) {
  return month ? `${path}?month=${encodeURIComponent(month)}` : path
}

/** GET /risk/households – simulated households of a month (default: latest). */
export function getV2Households(month) {
  return api(withMonth(`${V2}/risk/households`, month))
}

/** GET /risk/household/{key} – latest visit and timeline of one simulated household. */
export function getV2Household(householdKey) {
  return api(`${V2}/risk/household/${encodeURIComponent(householdKey)}`)
}

/** POST /risk/visit – score one visit. Nothing is stored. */
export function scoreV2Visit(body) {
  return api(`${V2}/risk/visit`, { method: "POST", body: JSON.stringify(body) })
}

/** GET /market/districts – 25 districts × 9 livelihoods for a month, with available_months. */
export function getV2MarketDistricts(month) {
  return api(withMonth(`${V2}/market/districts`, month))
}

/** GET /model/evidence – test results vs persistence, thresholds, limitations. */
export function getV2ModelEvidence() {
  return api(`${V2}/model/evidence`)
}

/** GET /households/{key}/recommendations – follow-up + action rules with official sources (FR4/FR5). */
export function getV2Recommendations(householdKey) {
  return api(`${V2}/households/${encodeURIComponent(householdKey)}/recommendations`)
}

/** POST /households/{key}/recommendations/{rule}/decision – the officer's decision (FR7). */
export function saveV2Decision(householdKey, ruleId, body) {
  return api(
    `${V2}/households/${encodeURIComponent(householdKey)}/recommendations/${encodeURIComponent(ruleId)}/decision`,
    { method: "POST", body: JSON.stringify(body) },
  )
}
