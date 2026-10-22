import { api } from "@/lib/api"

import { BASE_PATH } from "../constants"

export function getRiskModelInfo() {
  return api(`${BASE_PATH}/model-info`)
}

export function identifyCurrentRisk(signals) {
  return api(`${BASE_PATH}/identify`, {
    method: "POST",
    body: JSON.stringify(signals),
  })
}

export function predictMarketRisk(body) {
  return api(`${BASE_PATH}/predict`, {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function explainMarketRisk(body) {
  return api(`${BASE_PATH}/explain`, {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function getMarketContext(category, month) {
  const params = new URLSearchParams({ category, month })
  return api(`${BASE_PATH}/market-context?${params}`)
}
