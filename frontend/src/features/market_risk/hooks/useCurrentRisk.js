import { useQuery } from "@tanstack/react-query"

import { identifyCurrentRisk } from "../api/riskApi"
import { useDebouncedValue } from "./useDebouncedValue"

/**
 * POST /api/risk/identify for the current answers (the backend rule is the only source of
 * the class and counts), debounced like the history call. Same shape as useHistoryFeatures.
 */
export function useCurrentRisk(signals) {
  const key = JSON.stringify(signals)
  const debouncedKey = useDebouncedValue(key)
  const query = useQuery({
    queryKey: ["risk-current-class", debouncedKey],
    queryFn: () => identifyCurrentRisk(JSON.parse(debouncedKey)),
    staleTime: Infinity,
    retry: false,
  })
  const settled = key === debouncedKey
  return {
    query,
    waiting: !settled || query.isFetching,
    current: settled && query.isSuccess,
  }
}
