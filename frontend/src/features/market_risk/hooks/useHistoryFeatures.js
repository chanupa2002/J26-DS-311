import { useQuery } from "@tanstack/react-query"
import { useEffect, useState } from "react"

import { computeHistoryFeatures } from "../api/riskApi"

const DEBOUNCE_MS = 400

function useDebouncedValue(value, delay) {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])
  return debounced
}

/**
 * POST /api/risk/history-features for `request` (null = nothing to calculate), debounced.
 * `waiting` is true while typing has not settled or the request is loading, and `current`
 * is true only when the data belongs to the latest request.
 */
export function useHistoryFeatures(request) {
  const key = request ? JSON.stringify(request) : null
  const debouncedKey = useDebouncedValue(key, DEBOUNCE_MS)
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
