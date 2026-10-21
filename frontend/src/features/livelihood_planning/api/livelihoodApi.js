import { api } from "@/lib/api"

const BASE_PATH = "/api/livelihood"

export function getLivelihoodHealth() {
  return api(`${BASE_PATH}/health`)
}

export function getBeneficiaries() {
  return api(`${BASE_PATH}/beneficiaries`)
}

export function assessBeneficiary(beneficiaryId) {
  return api(`${BASE_PATH}/assess/${encodeURIComponent(beneficiaryId)}`, {
    method: "POST",
  })
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

export function getSwot(profile) {
  return api(`${BASE_PATH}/swot`, {
    method: "POST",
    body: JSON.stringify(profile),
  })
}
