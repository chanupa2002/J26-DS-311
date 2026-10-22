import { useMutation } from "@tanstack/react-query"

import { explainMarketRisk, predictMarketRisk } from "../api/riskApi"
import { TOP_K } from "../constants"

/**
 * Runs /predict and /explain in parallel with the same body (decision Q8).
 * Fails only if /predict fails; a failed /explain is returned as explainError,
 * so the prediction is still shown.
 */
async function predictAndExplain(body) {
  const [prediction, explanation] = await Promise.allSettled([
    predictMarketRisk(body),
    explainMarketRisk({ ...body, top_k: TOP_K }),
  ])
  if (prediction.status === "rejected") throw prediction.reason
  return {
    prediction: prediction.value,
    explanation: explanation.status === "fulfilled" ? explanation.value : null,
    explainError: explanation.status === "rejected" ? explanation.reason : null,
  }
}

export function useFutureRisk() {
  return useMutation({ mutationFn: predictAndExplain })
}
