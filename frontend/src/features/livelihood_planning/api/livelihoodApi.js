import { api } from "@/lib/api"

const BASE_PATH = "/api/livelihood"

/**
 * @typedef {{ id: string, title: string, summary: string, flag: "ok" | "note" | "warning", details: object }} DecisionTrailStep
 * @typedef {{ version: 1, recommendation: { steps: DecisionTrailStep[] }, swot?: { steps: DecisionTrailStep[] } }} DecisionTrail
 */

export function getLivelihoodHealth() {
  return api(`${BASE_PATH}/health`)
}

export function getBeneficiaries() {
  return api(`${BASE_PATH}/beneficiaries`)
}

export function assessBeneficiary(beneficiaryId, livelihood) {
  const options = { method: "POST" }
  if (livelihood) {
    options.body = JSON.stringify({ livelihood })
  }
  return api(
    `${BASE_PATH}/assess/${encodeURIComponent(beneficiaryId)}`,
    options,
  )
}

export function getAssessments(beneficiaryId) {
  return api(`${BASE_PATH}/assessments/${encodeURIComponent(beneficiaryId)}`)
}

export function getRecommendations(profile) {
  return api(`${BASE_PATH}/recommend`, {
    method: "POST",
    body: JSON.stringify(profile),
  })
}

export function getSwot(profile, livelihood) {
  const body = livelihood ? { ...profile, livelihood } : profile
  return api(`${BASE_PATH}/swot`, {
    method: "POST",
    body: JSON.stringify(body),
  })
}
