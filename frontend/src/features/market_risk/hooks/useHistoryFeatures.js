import { useQuery } from "@tanstack/react-query"

import { computeHistoryFeatures } from "../api/riskApi"
import { useDebouncedValue } from "./useDebouncedValue"

/**
 * POST /api/risk/history-features for `request` (null = nothing to calculate), debounced.
 * `waiting` is true while typing has not settled or the request is loading, and `current`
 * is true only when the data belongs to the latest request.
 */
export function useHistoryFeatures(request) {
  const key = request ? JSON.stringify(request) : null
  const debouncedKey = useDebouncedValue(key)
  const query = useQuery({
    queryKey: ["risk-history-features", debouncedKey],
    queryFn: () => computeHistoryFeatures(JSON.parse(debouncedKey)),
    enabled: Boolean(debouncedKey),
    staleTime: Infinity,
    retry: false,
  })
  const settled = key === debouncedKey
  return {
    query,
    waiting: Boolean(key) && (!settled || query.isFetching),
    current: Boolean(key) && settled && query.isSuccess,
  }
}
